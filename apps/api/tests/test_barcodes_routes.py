from __future__ import annotations

import httpx
import pytest

from app.models.category import Category
from app.models.item import Item
from app.models.location import Location
from app.services import barcode_service


def with_check(body: str) -> str:
    total = sum(
        int(ch) * (3 if i % 2 == 0 else 1) for i, ch in enumerate(reversed(body))
    )
    return f"{body}{(10 - total % 10) % 10}"


EAN = with_check("471008520001")
EAN2 = with_check("471008520002")
BAD_EAN = "4710085200014"  # 檢查碼壞 → unsupported
ISBN13 = with_check("978030640615")


async def _auth(client, username: str) -> dict[str, str]:
    await client.post(
        "/api/auth/register",
        json={
            "email": f"{username}@t.io",
            "username": username,
            "password": "secret1234",
        },
    )
    r = await client.post(
        "/api/auth/login", json={"username": username, "password": "secret1234"}
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _uid(client, headers) -> str:
    return (await client.get("/api/users/me", headers=headers)).json()["id"]


def _mock_http(monkeypatch, handler):
    calls = {"n": 0}

    def wrapped(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return handler(request)

    def factory() -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.MockTransport(wrapped), timeout=3.0)

    monkeypatch.setattr(barcode_service, "_client", factory)
    return calls


async def test_lookup_requires_authentication(client):
    r = await client.get(f"/api/barcodes/{EAN}")
    assert r.status_code == 401


async def test_lookup_single_local_match_with_canonical_input(client, db_session):
    headers = await _auth(client, "bc_single")
    uid = await _uid(client, headers)
    loc = Location(owner_id=uid, floor="1F", room="廚房", zone="上櫃")
    db_session.add(loc)
    await db_session.flush()
    item = Item(
        owner_id=uid,
        name="牛奶",
        barcode=ISBN13,
        quantity=2,
        location_id=loc.id,
    )
    db_session.add(item)
    await db_session.commit()

    # 帶連字號輸入 → 路由先 canonicalize 再精確比對
    r = await client.get("/api/barcodes/978-0-306-40615-7", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == ISBN13
    assert body["external_status"] == "skipped"
    assert body["external"] is None
    assert body["cached"] is False
    assert len(body["local_matches"]) == 1
    match = body["local_matches"][0]
    assert match["id"] == str(item.id)
    assert match["name"] == "牛奶"
    assert match["quantity"] == 2
    assert match["image_id"] is None
    assert match["location_path"] == "1F / 廚房 / 上櫃"


async def test_lookup_multi_local_matches_sorted_and_skips_external(
    client, db_session, monkeypatch
):
    headers = await _auth(client, "bc_multi")
    uid = await _uid(client, headers)
    db_session.add_all(
        [
            Item(owner_id=uid, name="B 牌牛奶", barcode=EAN, quantity=1),
            Item(owner_id=uid, name="A 牌牛奶", barcode=EAN, quantity=3),
        ]
    )
    await db_session.commit()
    calls = _mock_http(monkeypatch, lambda req: httpx.Response(500))

    r = await client.get(f"/api/barcodes/{EAN}", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["external_status"] == "skipped"
    assert [m["name"] for m in body["local_matches"]] == ["A 牌牛奶", "B 牌牛奶"]
    assert body["local_matches"][0]["location_path"] is None
    assert calls["n"] == 0  # 有內查命中 → 不打外部


async def test_lookup_external_hit_with_category_suggestion_and_cache(
    client, db_session, monkeypatch
):
    headers = await _auth(client, "bc_ext")
    uid = await _uid(client, headers)
    cat = Category(owner_id=uid, name="乳製品")
    db_session.add(cat)
    await db_session.commit()

    calls = _mock_http(
        monkeypatch,
        lambda req: httpx.Response(
            200,
            json={
                "status": 1,
                "product": {
                    "product_name": "鮮奶",
                    "brands": "瑞穗",
                    "categories": "乳製品, 飲料",
                    "quantity": "936ml",
                    "image_front_small_url": "https://img.example/milk.jpg",
                },
            },
        ),
    )

    r = await client.get(f"/api/barcodes/{EAN}", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["external_status"] == "ok"
    assert body["cached"] is False
    ext = body["external"]
    assert ext["source"] == "openfoodfacts"
    assert ext["name"] == "鮮奶"
    assert ext["description"] == "瑞穗，乳製品, 飲料，936ml"
    assert ext["image_url"] == "https://img.example/milk.jpg"
    assert ext["suggested_category_id"] == cat.id
    assert calls["n"] == 1

    again = (await client.get(f"/api/barcodes/{EAN}", headers=headers)).json()
    assert again["cached"] is True
    assert again["external"]["name"] == "鮮奶"
    assert calls["n"] == 1


async def test_lookup_external_not_found(client, db_session, monkeypatch):
    headers = await _auth(client, "bc_miss")
    _mock_http(monkeypatch, lambda req: httpx.Response(200, json={"status": 0}))

    r = await client.get(f"/api/barcodes/{EAN2}", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["external_status"] == "not_found"
    assert body["external"] is None
    assert body["local_matches"] == []


async def test_lookup_external_unavailable_is_fail_soft(client, monkeypatch):
    headers = await _auth(client, "bc_timeout")

    def handler(req):
        raise httpx.TimeoutException("timed out")

    _mock_http(monkeypatch, handler)

    r = await client.get(f"/api/barcodes/{EAN}", headers=headers)
    assert r.status_code == 200  # fail-soft：不是 5xx
    body = r.json()
    assert body["external_status"] == "unavailable"
    assert body["external"] is None


async def test_lookup_unsupported_never_calls_external(client, monkeypatch):
    headers = await _auth(client, "bc_unsupported")
    calls = _mock_http(monkeypatch, lambda req: httpx.Response(500))

    r = await client.get(f"/api/barcodes/{BAD_EAN}", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["external_status"] == "unsupported"
    assert calls["n"] == 0


async def test_lookup_invalid_codes_422(client):
    headers = await _auth(client, "bc_invalid")

    assert (await client.get("/api/barcodes/%20", headers=headers)).status_code == 422
    long_code = "9" * 65
    assert (
        await client.get(f"/api/barcodes/{long_code}", headers=headers)
    ).status_code == 422


async def test_lookup_owner_isolation(client, db_session, monkeypatch):
    owner_headers = await _auth(client, "bc_owner_a")
    uid = await _uid(client, owner_headers)
    db_session.add(Item(owner_id=uid, name="私人物品", barcode="ABC-123"))
    await db_session.commit()
    other_headers = await _auth(client, "bc_owner_b")
    calls = _mock_http(monkeypatch, lambda req: httpx.Response(500))

    r = await client.get("/api/barcodes/ABC-123", headers=other_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["local_matches"] == []
    assert body["external_status"] == "unsupported"
    assert calls["n"] == 0
