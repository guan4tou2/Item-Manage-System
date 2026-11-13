from __future__ import annotations

import struct
import uuid
import zlib
from unittest.mock import MagicMock

import pytest
from sqlalchemy import select

from app.models.ai_draft import AiDraftItem

_AI_JSON = (
    '{"name":"陶瓷咖啡杯","description":"陶瓷馬克杯","category_suggestion":"廚房用品",'
    '"tag_suggestions":["咖啡","陶瓷"]}'
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


def _configure(monkeypatch, *, key: str | None, quota: int | None = None) -> None:
    if key is None:
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    else:
        monkeypatch.setenv("GEMINI_API_KEY", key)
    if quota is not None:
        monkeypatch.setenv("AI_DAILY_QUOTA", str(quota))
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


async def _draft(client, headers: dict, image_id: str) -> dict:
    r = await client.post("/api/ai/drafts", headers=headers, json={"image_ids": [image_id]})
    assert r.status_code == 201
    return r.json()["created"][0]


async def _seed_history(client, headers: dict) -> None:
    category = (
        await client.post("/api/categories", headers=headers, json={"name": "廚房用品"})
    ).json()
    r = await client.post(
        "/api/items",
        headers=headers,
        json={"name": "陶瓷咖啡杯", "category_id": category["id"]},
    )
    assert r.status_code == 201


async def test_process_success_sets_ready_with_ai_and_history(client, monkeypatch):
    _configure(monkeypatch, key="fake-key")
    fake_client = _mock_gemini(monkeypatch)
    auth = await _login(client, "proc_a")
    await _seed_history(client, auth)
    draft = await _draft(client, auth, await _upload(client, auth))

    r = await client.post(f"/api/ai/drafts/{draft['id']}/process", headers=auth)

    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ready"
    assert body["error_code"] is None
    assert body["processed_at"] is not None
    assert body["payload"]["version"] == 1
    assert body["payload"]["ai"] == {
        "name": "陶瓷咖啡杯",
        "description": "陶瓷馬克杯",
        "category_suggestion": "廚房用品",
        "tag_suggestions": ["咖啡", "陶瓷"],
    }
    assert body["payload"]["history"]["category"]["name"] == "廚房用品"
    assert body["payload"]["history"]["tags"] == []
    assert fake_client.models.generate_content.call_count == 1


async def test_process_without_api_key_fails_with_ai_disabled(client, monkeypatch):
    _configure(monkeypatch, key=None)
    auth = await _login(client, "proc_b")
    draft = await _draft(client, auth, await _upload(client, auth))

    r = await client.post(f"/api/ai/drafts/{draft['id']}/process", headers=auth)

    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "failed"
    assert body["error_code"] == "ai_disabled"
    assert body["processed_at"] is not None
    assert body["payload"]["ai"] is None
    assert body["payload"]["history"] == {
        "category": None,
        "location": None,
        "tags": [],
    }


async def test_process_quota_exhausted_skips_gemini(client, monkeypatch):
    _configure(monkeypatch, key="fake-key", quota=1)
    fake_client = _mock_gemini(monkeypatch)
    auth = await _login(client, "proc_c")
    first = await _draft(client, auth, await _upload(client, auth))
    second = await _draft(client, auth, await _upload(client, auth))

    assert (
        await client.post(f"/api/ai/drafts/{first['id']}/process", headers=auth)
    ).json()["status"] == "ready"

    r = await client.post(f"/api/ai/drafts/{second['id']}/process", headers=auth)
    assert r.json()["status"] == "failed"
    assert r.json()["error_code"] == "quota_exhausted"
    assert fake_client.models.generate_content.call_count == 1


async def test_process_upstream_exception_maps_to_upstream_error(client, monkeypatch):
    _configure(monkeypatch, key="fake-key")
    fake_client = MagicMock()
    fake_client.models.generate_content.side_effect = RuntimeError("boom")
    monkeypatch.setattr("google.genai.Client", lambda api_key: fake_client)
    auth = await _login(client, "proc_d")
    draft = await _draft(client, auth, await _upload(client, auth))

    r = await client.post(f"/api/ai/drafts/{draft['id']}/process", headers=auth)

    assert r.status_code == 200
    assert r.json()["status"] == "failed"
    assert r.json()["error_code"] == "upstream_error"


async def test_process_invalid_json_maps_to_upstream_error(client, monkeypatch):
    _configure(monkeypatch, key="fake-key")
    _mock_gemini(monkeypatch, text="not json at all")
    auth = await _login(client, "proc_e")
    draft = await _draft(client, auth, await _upload(client, auth))

    r = await client.post(f"/api/ai/drafts/{draft['id']}/process", headers=auth)

    assert r.json()["status"] == "failed"
    assert r.json()["error_code"] == "upstream_error"


async def test_process_deleted_image_maps_to_image_missing(client, monkeypatch):
    _configure(monkeypatch, key="fake-key")
    fake_client = _mock_gemini(monkeypatch)
    auth = await _login(client, "proc_f")
    image_id = await _upload(client, auth)
    draft = await _draft(client, auth, image_id)

    deleted = await client.delete(f"/api/images/{image_id}", headers=auth)
    assert deleted.status_code == 204

    r = await client.post(f"/api/ai/drafts/{draft['id']}/process", headers=auth)

    assert r.json()["status"] == "failed"
    assert r.json()["error_code"] == "image_missing"
    assert fake_client.models.generate_content.call_count == 0


async def test_process_retry_after_failure_clears_error(client, monkeypatch):
    _configure(monkeypatch, key=None)
    auth = await _login(client, "proc_g")
    draft = await _draft(client, auth, await _upload(client, auth))
    failed = (
        await client.post(f"/api/ai/drafts/{draft['id']}/process", headers=auth)
    ).json()
    assert failed["error_code"] == "ai_disabled"

    # 設定 key 後重試 → ready 且 error_code 清空
    _configure(monkeypatch, key="fake-key")
    _mock_gemini(monkeypatch)
    retried = (
        await client.post(f"/api/ai/drafts/{draft['id']}/process", headers=auth)
    ).json()
    assert retried["status"] == "ready"
    assert retried["error_code"] is None


async def test_process_allowed_from_ready_and_processing(client, monkeypatch, db_session):
    _configure(monkeypatch, key="fake-key")
    _mock_gemini(monkeypatch)
    auth = await _login(client, "proc_h")
    draft = await _draft(client, auth, await _upload(client, auth))

    assert (
        await client.post(f"/api/ai/drafts/{draft['id']}/process", headers=auth)
    ).json()["status"] == "ready"
    # ready 可重跑
    assert (
        await client.post(f"/api/ai/drafts/{draft['id']}/process", headers=auth)
    ).json()["status"] == "ready"

    # processing（伺服器曾中斷）可重入
    row = (
        await db_session.execute(
            select(AiDraftItem).where(AiDraftItem.id == uuid.UUID(draft["id"]))
        )
    ).scalar_one()
    row.status = "processing"
    await db_session.commit()
    assert (
        await client.post(f"/api/ai/drafts/{draft['id']}/process", headers=auth)
    ).json()["status"] == "ready"


async def test_process_terminal_states_conflict(client, monkeypatch, db_session):
    _configure(monkeypatch, key="fake-key")
    _mock_gemini(monkeypatch)
    auth = await _login(client, "proc_i")
    draft = await _draft(client, auth, await _upload(client, auth))

    row = (
        await db_session.execute(
            select(AiDraftItem).where(AiDraftItem.id == uuid.UUID(draft["id"]))
        )
    ).scalar_one()
    for terminal in ("accepted", "discarded"):
        row.status = terminal
        await db_session.commit()
        r = await client.post(f"/api/ai/drafts/{draft['id']}/process", headers=auth)
        assert r.status_code == 409
        assert terminal in r.json()["detail"]


async def test_process_not_found_and_viewer_blocked(client, monkeypatch):
    _configure(monkeypatch, key="fake-key")
    _mock_gemini(monkeypatch)
    auth = await _login(client, "proc_j")
    other = await _login(client, "proc_j_other")
    draft = await _draft(client, auth, await _upload(client, auth))

    missing = await client.post(
        f"/api/ai/drafts/{uuid.uuid4()}/process", headers=auth
    )
    assert missing.status_code == 404

    foreign = await client.post(
        f"/api/ai/drafts/{draft['id']}/process", headers=other
    )
    assert foreign.status_code == 404


async def test_process_viewer_blocked(client, monkeypatch):
    _configure(monkeypatch, key="fake-key")
    owner = await _login(client, "proc_viewer_owner")
    viewer = await _login(client, "proc_viewer")
    gid = (
        await client.post("/api/groups", headers=owner, json={"name": "g-viewer"})
    ).json()["id"]
    r = await client.post(
        f"/api/groups/{gid}/members",
        headers=owner,
        json={"username": "proc_viewer", "role": "viewer"},
    )
    assert r.status_code == 201
    draft = await _draft(client, owner, await _upload(client, owner))

    blocked = await client.post(f"/api/ai/drafts/{draft['id']}/process", headers=viewer)
    assert blocked.status_code == 403


# --- Phase 33：收據草稿的狀態機邊界 ------------------------------------------


async def test_process_receipt_draft_is_409(client, monkeypatch):
    """收據草稿於建立時即抽取完成 → process 一律 409（不重跑 LLM）。"""

    _configure(monkeypatch, key="fake-key")
    _mock_gemini(
        monkeypatch,
        '{"merchant":"全聯","purchased_at":null,"currency":"TWD","total":"10.00",'
        '"items":[{"name":"鮮乳","quantity":1,"unit_price":"10.00","subtotal":"10.00"}]}',
    )
    auth = await _login(client, "proc_receipt")
    page = await _upload(client, auth)
    created = await client.post(
        "/api/ai/receipts", headers=auth, json={"image_ids": [page]}
    )
    draft_id = created.json()["created"][0]["id"]

    r = await client.post(f"/api/ai/drafts/{draft_id}/process", headers=auth)

    assert r.status_code == 409
    assert "receipt" in r.json()["detail"]


async def test_process_receipt_draft_does_not_call_llm(client, monkeypatch):
    _configure(monkeypatch, key="fake-key")
    fake_client = _mock_gemini(
        monkeypatch,
        '{"merchant":null,"purchased_at":null,"currency":null,"total":null,'
        '"items":[{"name":"鮮乳","quantity":1,"unit_price":"10.00","subtotal":"10.00"}]}',
    )
    auth = await _login(client, "proc_receipt2")
    page = await _upload(client, auth)
    created = await client.post(
        "/api/ai/receipts", headers=auth, json={"image_ids": [page]}
    )
    draft_id = created.json()["created"][0]["id"]
    calls_after_create = fake_client.models.generate_content.call_count

    await client.post(f"/api/ai/drafts/{draft_id}/process", headers=auth)

    assert fake_client.models.generate_content.call_count == calls_after_create
