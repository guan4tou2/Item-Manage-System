from __future__ import annotations

import struct
import uuid
import zlib
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import select

from app.models.ai_draft import AiDraftItem

_AI_JSON = (
    '{"name":"陶瓷咖啡杯","description":"陶瓷馬克杯","category_suggestion":"廚房用品",'
    '"tag_suggestions":["咖啡"]}'
)


def _tiny_png() -> bytes:
    signature = b"\x89PNG\r\n\x1a\n"

    def chunk(tag: bytes, data: bytes) -> bytes:
        import zlib as z

        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", z.crc32(tag + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    raw = b"\x00\x00\xff\x00"
    idat = zlib.compress(raw)
    return signature + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


@pytest.fixture(autouse=True)
def _media_env(tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path))
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("AI_DAILY_QUOTA", raising=False)
    from app.config import get_settings

    get_settings.cache_clear()


def _configure(monkeypatch, *, key: str | None) -> None:
    if key is None:
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    else:
        monkeypatch.setenv("GEMINI_API_KEY", key)
    from app.config import get_settings

    get_settings.cache_clear()


def _mock_gemini(monkeypatch, text: str = _AI_JSON) -> MagicMock:
    fake_response = MagicMock()
    fake_response.text = text
    fake_client = MagicMock()
    fake_client.models.generate_content.return_value = fake_response
    monkeypatch.setattr("google.genai.Client", lambda api_key: fake_client)
    return fake_client


async def _login(client, username: str) -> dict:
    await client.post(
        "/api/auth/register",
        json={"email": f"{username}@t.io", "username": username, "password": "secret1234"},
    )
    r = await client.post(
        "/api/auth/login", json={"username": username, "password": "secret1234"}
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _upload(client, headers: dict) -> str:
    files = {"file": ("x.png", _tiny_png(), "image/png")}
    r = await client.post("/api/images", headers=headers, files=files)
    assert r.status_code == 201
    return r.json()["id"]


async def _draft(client, headers: dict) -> dict:
    image_id = await _upload(client, headers)
    r = await client.post(
        "/api/ai/drafts", headers=headers, json={"image_ids": [image_id]}
    )
    assert r.status_code == 201
    draft = r.json()["created"][0]
    draft["_image_id"] = image_id
    return draft


async def _ready_draft(client, headers: dict) -> dict:
    draft = await _draft(client, headers)
    processed = await client.post(
        f"/api/ai/drafts/{draft['id']}/process", headers=headers
    )
    assert processed.status_code == 200
    assert processed.json()["status"] == "ready"
    return processed.json()


async def _category(client, headers: dict, name: str = "廚房用品") -> int:
    r = await client.post("/api/categories", headers=headers, json={"name": name})
    assert r.status_code == 201
    return r.json()["id"]


async def _location(client, headers: dict, name: str = "廚房") -> int:
    r = await client.post("/api/locations", headers=headers, json={"name": name})
    assert r.status_code == 201
    return r.json()["id"]


async def _member_auth(client, name: str, role: str) -> dict:
    owner = await _login(client, f"{name}_owner")
    member = await _login(client, name)
    gid = (
        await client.post("/api/groups", headers=owner, json={"name": f"g-{name}"})
    ).json()["id"]
    r = await client.post(
        f"/api/groups/{gid}/members",
        headers=owner,
        json={"username": name, "role": role},
    )
    assert r.status_code == 201
    return member


async def test_accept_creates_item_with_edited_fields(client, monkeypatch):
    _configure(monkeypatch, key="fake-key")
    _mock_gemini(monkeypatch)
    auth = await _login(client, "acc_a")
    category_id = await _category(client, auth)
    location_id = await _location(client, auth)
    draft = await _ready_draft(client, auth)

    r = await client.post(
        f"/api/ai/drafts/{draft['id']}/accept",
        headers=auth,
        json={
            "name": "咖啡濾杯",
            "description": "陶瓷手沖濾杯",
            "category_id": category_id,
            "location_id": location_id,
            "tag_names": ["咖啡", "陶瓷"],
            "quantity": 2,
            "cost": "450.00",
        },
    )

    assert r.status_code == 200
    body = r.json()
    assert body["draft"]["status"] == "accepted"
    assert body["draft"]["item_id"] == body["item"]["id"]
    item = body["item"]
    assert item["name"] == "咖啡濾杯"
    assert item["description"] == "陶瓷手沖濾杯"
    assert item["category"]["id"] == category_id
    assert item["location"]["id"] == location_id
    assert sorted(tag["name"] for tag in item["tags"]) == ["咖啡", "陶瓷"]
    assert item["quantity"] == 2
    assert item["cost"] == "450.00"
    assert item["image_id"] == draft["image_id"]

    # accepted 草稿離開活動佇列、可用 status 查得
    active = await client.get("/api/ai/drafts", headers=auth)
    assert active.json()["items"] == []
    accepted = await client.get("/api/ai/drafts?status=accepted", headers=auth)
    assert [d["id"] for d in accepted.json()["items"]] == [draft["id"]]

    # 物品確實落地
    items = await client.get("/api/items", headers=auth)
    assert [i["name"] for i in items.json()["items"]] == ["咖啡濾杯"]


async def test_accept_from_failed_allows_manual_completion(client, monkeypatch):
    _configure(monkeypatch, key=None)
    auth = await _login(client, "acc_b")
    draft = await _draft(client, auth)
    failed = (
        await client.post(f"/api/ai/drafts/{draft['id']}/process", headers=auth)
    ).json()
    assert failed["status"] == "failed"

    r = await client.post(
        f"/api/ai/drafts/{draft['id']}/accept",
        headers=auth,
        json={"name": "手動填寫物品"},
    )

    assert r.status_code == 200
    assert r.json()["draft"]["status"] == "accepted"
    assert r.json()["item"]["name"] == "手動填寫物品"
    assert r.json()["item"]["image_id"] == draft["image_id"]


async def test_accept_pending_or_processing_conflicts(client, monkeypatch, db_session):
    _configure(monkeypatch, key="fake-key")
    _mock_gemini(monkeypatch)
    auth = await _login(client, "acc_c")
    draft = await _draft(client, auth)

    pending = await client.post(
        f"/api/ai/drafts/{draft['id']}/accept", headers=auth, json={"name": "X"}
    )
    assert pending.status_code == 409

    row = (
        await db_session.execute(
            select(AiDraftItem).where(AiDraftItem.id == uuid.UUID(draft["id"]))
        )
    ).scalar_one()
    row.status = "processing"
    await db_session.commit()

    processing = await client.post(
        f"/api/ai/drafts/{draft['id']}/accept", headers=auth, json={"name": "X"}
    )
    assert processing.status_code == 409


async def test_accept_twice_conflicts(client, monkeypatch):
    _configure(monkeypatch, key="fake-key")
    _mock_gemini(monkeypatch)
    auth = await _login(client, "acc_d")
    draft = await _ready_draft(client, auth)

    first = await client.post(
        f"/api/ai/drafts/{draft['id']}/accept", headers=auth, json={"name": "咖啡杯"}
    )
    assert first.status_code == 200

    second = await client.post(
        f"/api/ai/drafts/{draft['id']}/accept", headers=auth, json={"name": "咖啡杯"}
    )
    assert second.status_code == 409
    assert "accepted" in second.json()["detail"]


async def test_accept_validation_and_ownership(client, monkeypatch):
    _configure(monkeypatch, key="fake-key")
    _mock_gemini(monkeypatch)
    auth = await _login(client, "acc_e")
    other = await _login(client, "acc_e_other")
    draft = await _ready_draft(client, auth)

    blank = await client.post(
        f"/api/ai/drafts/{draft['id']}/accept", headers=auth, json={"name": ""}
    )
    assert blank.status_code == 422

    extra = await client.post(
        f"/api/ai/drafts/{draft['id']}/accept",
        headers=auth,
        json={"name": "X", "warehouse_id": 1},
    )
    assert extra.status_code == 422

    bad_category = await client.post(
        f"/api/ai/drafts/{draft['id']}/accept",
        headers=auth,
        json={"name": "X", "category_id": 999999},
    )
    assert bad_category.status_code == 422

    foreign = await client.post(
        f"/api/ai/drafts/{draft['id']}/accept", headers=other, json={"name": "X"}
    )
    assert foreign.status_code == 404

    missing = await client.post(
        f"/api/ai/drafts/{uuid.uuid4()}/accept", headers=auth, json={"name": "X"}
    )
    assert missing.status_code == 404

    viewer = await _member_auth(client, "acc_viewer", "viewer")
    blocked = await client.post(
        f"/api/ai/drafts/{draft['id']}/accept", headers=viewer, json={"name": "X"}
    )
    assert blocked.status_code == 403


async def test_accept_dispatches_item_created_webhook(client, monkeypatch):
    _configure(monkeypatch, key="fake-key")
    _mock_gemini(monkeypatch)

    class MockResponse:
        status_code = 200
        text = "OK"

    mock_post = AsyncMock(return_value=MockResponse())
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = mock_post
    import httpx

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: mock_client)

    auth = await _login(client, "acc_f")
    await client.post(
        "/api/webhooks",
        headers=auth,
        json={"name": "t", "url": "http://example.com/hook", "events": ["item.created"]},
    )
    draft = await _ready_draft(client, auth)

    r = await client.post(
        f"/api/ai/drafts/{draft['id']}/accept", headers=auth, json={"name": "咖啡杯"}
    )
    assert r.status_code == 200
    assert mock_post.called


async def test_discard_single_states(client, monkeypatch, db_session):
    _configure(monkeypatch, key="fake-key")
    _mock_gemini(monkeypatch)
    auth = await _login(client, "dis_a")
    other = await _login(client, "dis_a_other")

    pending = await _draft(client, auth)
    ok = await client.post(f"/api/ai/drafts/{pending['id']}/discard", headers=auth)
    assert ok.status_code == 200
    assert ok.json()["status"] == "discarded"

    again = await client.post(f"/api/ai/drafts/{pending['id']}/discard", headers=auth)
    assert again.status_code == 409
    assert "discarded" in again.json()["detail"]

    ready = await _ready_draft(client, auth)
    assert (
        await client.post(f"/api/ai/drafts/{ready['id']}/discard", headers=auth)
    ).json()["status"] == "discarded"

    foreign = await client.post(f"/api/ai/drafts/{ready['id']}/discard", headers=other)
    assert foreign.status_code == 404

    missing = await client.post(
        f"/api/ai/drafts/{uuid.uuid4()}/discard", headers=auth
    )
    assert missing.status_code == 404

    viewer = await _member_auth(client, "dis_viewer", "viewer")
    blocked = await client.post(f"/api/ai/drafts/{ready['id']}/discard", headers=viewer)
    assert blocked.status_code == 403


async def test_bulk_discard_mixed_input(client, monkeypatch):
    _configure(monkeypatch, key="fake-key")
    _mock_gemini(monkeypatch)
    auth = await _login(client, "dis_b")

    first = await _draft(client, auth)
    second = await _ready_draft(client, auth)
    third = await _ready_draft(client, auth)
    accepted = await client.post(
        f"/api/ai/drafts/{third['id']}/accept", headers=auth, json={"name": "已建立"}
    )
    assert accepted.status_code == 200
    ghost = str(uuid.uuid4())

    r = await client.post(
        "/api/ai/drafts/discard",
        headers=auth,
        json={"ids": [first["id"], second["id"], third["id"], ghost]},
    )

    assert r.status_code == 200
    body = r.json()
    assert body["discarded"] == 2
    skipped = {item["id"]: item["reason"] for item in body["skipped"]}
    assert skipped == {
        third["id"]: "already accepted",
        ghost: "not found",
    }

    remaining = await client.get("/api/ai/drafts", headers=auth)
    assert remaining.json()["items"] == []


async def test_bulk_discard_validation_and_viewer(client, monkeypatch):
    _configure(monkeypatch, key="fake-key")
    auth = await _login(client, "dis_c")

    empty = await client.post(
        "/api/ai/drafts/discard", headers=auth, json={"ids": []}
    )
    assert empty.status_code == 422

    many = await client.post(
        "/api/ai/drafts/discard",
        headers=auth,
        json={"ids": [str(uuid.uuid4())] * 51},
    )
    assert many.status_code == 422

    viewer = await _member_auth(client, "dis_viewer2", "viewer")
    blocked = await client.post(
        "/api/ai/drafts/discard", headers=viewer, json={"ids": [str(uuid.uuid4())]}
    )
    assert blocked.status_code == 403
