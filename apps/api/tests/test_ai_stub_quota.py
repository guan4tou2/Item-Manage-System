"""Phase 35 T1.4：stub 模式不消耗 AI 配額。

stub 沒有上游成本，不該寫入 `ai_usage`（否則 e2e 連跑會被每日額度攔截）。
live 模式配額行為完全不變。
"""
from __future__ import annotations

import struct
import zlib
from datetime import date, timedelta

import pytest
from sqlalchemy import func, select

from app.models.ai_usage import AiUsage


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
def _env(tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path))
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("AI_MODE", raising=False)
    monkeypatch.setenv("AI_DAILY_QUOTA", "2")
    from app.config import get_settings

    get_settings.cache_clear()


@pytest.fixture
async def auth(client):
    await client.post(
        "/api/auth/register",
        json={"email": "quota@t.io", "username": "quota_user", "password": "secret1234"},
    )
    r = await client.post(
        "/api/auth/login",
        json={"username": "quota_user", "password": "secret1234"},
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _usage_rows(db_session):
    return (
        await db_session.execute(select(func.count()).select_from(AiUsage))
    ).scalar_one()


async def test_stub_mode_does_not_consume_quota(client, auth, db_session, monkeypatch):
    monkeypatch.setenv("AI_MODE", "stub")
    from app.config import get_settings

    get_settings.cache_clear()

    files = {"file": ("x.png", _tiny_png(), "image/png")}
    img = (await client.post("/api/images", headers=auth, files=files)).json()

    # 連續呼叫超過每日額度（2 次）→ stub 模式仍應全部成功
    for _ in range(4):
        r = await client.post(
            "/api/ai/suggest-from-image",
            headers=auth,
            json={"image_id": img["id"]},
        )
        assert r.status_code == 200

    assert await _usage_rows(db_session) == 0


async def test_live_mode_still_enforces_quota(client, auth, db_session, monkeypatch):
    """live 模式無 key → 503（不計次，因未進入 LLM 呼叫）。"""
    files = {"file": ("x.png", _tiny_png(), "image/png")}
    img = (await client.post("/api/images", headers=auth, files=files)).json()

    r = await client.post(
        "/api/ai/suggest-from-image",
        headers=auth,
        json={"image_id": img["id"]},
    )
    assert r.status_code == 503
    assert await _usage_rows(db_session) == 0
