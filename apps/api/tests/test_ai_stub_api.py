"""Phase 35 T1.3：stub 模式下的 API 行為。

- stub 模式（無 key）：建議／收據／搜尋／問答**成功路徑**可用
- live 模式（無 key）：既有 fallback／503 行為**完全不變**
- stub 回應仍走真實解析／白名單／引用映射（越界引用不產生 citation）
"""
from __future__ import annotations

import struct
import uuid
import zlib

import pytest


def _tiny_png() -> bytes:
    signature = b"\x89PNG\r\n\x1a\n"

    def chunk(tag: bytes, data: bytes) -> bytes:
        import zlib as z

        return (
            signature
            + struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", z.crc32(tag + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    raw = b"\x00\x00\xff\x00"
    idat = zlib.compress(raw)
    return chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


@pytest.fixture(autouse=True)
def _media_env(tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path))
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("AI_DAILY_QUOTA", raising=False)
    monkeypatch.delenv("AI_MODE", raising=False)
    from app.config import get_settings

    get_settings.cache_clear()


@pytest.fixture
async def auth(client):
    await client.post(
        "/api/auth/register",
        json={"email": "stub@t.io", "username": "stub_user", "password": "secret1234"},
    )
    r = await client.post(
        "/api/auth/login",
        json={"username": "stub_user", "password": "secret1234"},
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _enable_stub(monkeypatch) -> None:
    monkeypatch.setenv("AI_MODE", "stub")
    from app.config import get_settings

    get_settings.cache_clear()


def _enable_opt_in(client, auth) -> None:
    r = await_put_preferences(client, auth)
    assert r.status_code == 200
    assert r.json()["ai_data_sharing_enabled"] is True


async def await_put_preferences(client, auth):
    return await client.put(
        "/api/users/me/preferences",
        headers=auth,
        json={"ai_data_sharing_enabled": True},
    )


# --- 建議 ---------------------------------------------------------------


async def test_stub_suggest_returns_stub_payload(client, auth, monkeypatch):
    _enable_stub(monkeypatch)
    files = {"file": ("x.png", _tiny_png(), "image/png")}
    img = (await client.post("/api/images", headers=auth, files=files)).json()

    r = await client.post(
        "/api/ai/suggest-from-image",
        headers=auth,
        json={"image_id": img["id"]},
    )
    assert r.status_code == 200
    assert r.json()["name"] == "測試物品"
    assert r.json()["category_suggestion"] == "測試分類"


async def test_live_without_key_still_503(client, auth):
    """live 模式無 key → 既有 503 行為不變。"""
    files = {"file": ("x.png", _tiny_png(), "image/png")}
    img = (await client.post("/api/images", headers=auth, files=files)).json()
    r = await client.post(
        "/api/ai/suggest-from-image",
        headers=auth,
        json={"image_id": img["id"]},
    )
    assert r.status_code == 503


# --- 收據 ---------------------------------------------------------------


async def test_stub_receipt_creates_ready_drafts(client, auth, monkeypatch):
    _enable_stub(monkeypatch)
    files = {"file": ("r.png", _tiny_png(), "image/png")}
    img = (await client.post("/api/images", headers=auth, files=files)).json()

    r = await client.post(
        "/api/ai/receipts",
        headers=auth,
        json={"image_ids": [img["id"]]},
    )
    assert r.status_code == 201
    body = r.json()
    assert len(body["created"]) == 2
    assert all(row["status"] == "ready" for row in body["created"])
    snapshot = body["created"][0]["payload"]["receipt"]
    assert snapshot["merchant"] == "測試商店"
    # 對帳相符：總額 == 品項合計（差額 0）
    assert snapshot["total"] == snapshot["item_total"]
    assert snapshot["discrepancy"] == "0.00"


async def test_live_receipt_without_key_still_503(client, auth):
    files = {"file": ("r.png", _tiny_png(), "image/png")}
    img = (await client.post("/api/images", headers=auth, files=files)).json()
    r = await client.post(
        "/api/ai/receipts",
        headers=auth,
        json={"image_ids": [img["id"]]},
    )
    assert r.status_code == 503
    assert r.json()["detail"] == "ai_disabled"


# --- 搜尋 ---------------------------------------------------------------


async def test_stub_search_returns_applied_filters(client, auth, monkeypatch):
    _enable_stub(monkeypatch)
    await await_put_preferences(client, auth)

    location = await client.post(
        "/api/locations", headers=auth, json={"name": "廚房"}
    )
    location_id = location.json()["id"]
    item = await client.post(
        "/api/items",
        headers=auth,
        json={"name": "感冒藥", "location_id": location_id},
    )
    assert item.status_code == 201
    # 到期篩選依批次到期日（Phase 22）→ 補一顆 3 天內到期的批次
    from datetime import date, timedelta

    batch = await client.post(
        f"/api/items/{item.json()['id']}/batches",
        headers=auth,
        json={"quantity": 1, "expiry_date": (date.today() + timedelta(days=3)).isoformat()},
    )
    assert batch.status_code == 201

    r = await client.post(
        "/api/ai/search",
        headers=auth,
        json={"query": "廚房裡快過期的感冒藥"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["fallback_reason"] is None
    assert body["applied"]["location"]["name"] == "廚房"
    assert body["applied"]["expiry"] == "expiring_soon"
    assert body["applied"]["q"] == "感冒藥"
    assert body["total"] >= 1


async def test_stub_search_without_opt_in_still_403(client, auth, monkeypatch):
    _enable_stub(monkeypatch)
    r = await client.post(
        "/api/ai/search", headers=auth, json={"query": "感冒藥"}
    )
    assert r.status_code == 403
    assert r.json()["detail"] == "ai_opt_in_required"


async def test_live_search_without_key_falls_back(client, auth):
    await await_put_preferences(client, auth)
    r = await client.post(
        "/api/ai/search", headers=auth, json={"query": "感冒藥"}
    )
    assert r.status_code == 200
    assert r.json()["fallback_reason"] == "ai_disabled"


# --- 問答 ---------------------------------------------------------------


async def test_stub_ask_returns_citations(client, auth, monkeypatch):
    _enable_stub(monkeypatch)
    await await_put_preferences(client, auth)

    item = await client.post(
        "/api/items", headers=auth, json={"name": "感冒藥", "quantity": 2}
    )
    item_id = item.json()["id"]

    r = await client.post(
        "/api/ai/ask",
        headers=auth,
        json={"question": "有哪些東西？", "item_ids": [item_id]},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["grounded"] is True
    assert body["citations"][0]["item_id"] == item_id
    assert body["citations"][0]["name"] == "感冒藥"


async def test_stub_ask_drops_out_of_range_citation(client, auth, monkeypatch):
    """越界引用（[#9]）不得產生 citation。"""
    _enable_stub(monkeypatch)
    await await_put_preferences(client, auth)

    item = await client.post(
        "/api/items", headers=auth, json={"name": "感冒藥"}
    )
    item_id = item.json()["id"]

    from app.services import ai_service

    original = ai_service.ai_stub.ask_text

    def patched(question, context):
        return original(question, context).replace("[#1]", "[#9]")

    monkeypatch.setattr(ai_service.ai_stub, "ask_text", patched)

    r = await client.post(
        "/api/ai/ask",
        headers=auth,
        json={"question": "有哪些東西？", "item_ids": [item_id]},
    )
    assert r.status_code == 200
    assert r.json()["citations"] == []


async def test_live_ask_without_key_still_503(client, auth):
    await await_put_preferences(client, auth)
    r = await client.post(
        "/api/ai/ask", headers=auth, json={"question": "有哪些東西？"}
    )
    assert r.status_code == 503
    assert r.json()["detail"] == "ai_disabled"


# --- 草稿 process -------------------------------------------------------


async def test_stub_draft_process_becomes_ready(client, auth, monkeypatch):
    _enable_stub(monkeypatch)
    files = {"file": ("p.png", _tiny_png(), "image/png")}
    img = (await client.post("/api/images", headers=auth, files=files)).json()

    created = await client.post(
        "/api/ai/drafts", headers=auth, json={"image_ids": [img["id"]]}
    )
    assert created.status_code == 201
    draft_id = created.json()["created"][0]["id"]

    r = await client.post(
        f"/api/ai/drafts/{draft_id}/process", headers=auth
    )
    assert r.status_code == 200
    assert r.json()["status"] == "ready"
    assert r.json()["payload"]["ai"]["name"] == "測試物品"


async def test_live_draft_process_without_key_fails(client, auth):
    files = {"file": ("p.png", _tiny_png(), "image/png")}
    img = (await client.post("/api/images", headers=auth, files=files)).json()
    created = await client.post(
        "/api/ai/drafts", headers=auth, json={"image_ids": [img["id"]]}
    )
    draft_id = created.json()["created"][0]["id"]

    r = await client.post(f"/api/ai/drafts/{draft_id}/process", headers=auth)
    assert r.status_code == 200
    assert r.json()["status"] == "failed"
    assert r.json()["error_code"] == "ai_disabled"
