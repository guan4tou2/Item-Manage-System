"""Phase 35 T1.5：`GET /api/ai/status`（模式與啟用狀態）。

- 需登入（viewer 亦可；唯讀）
- 回 `{mode: "live"|"stub", enabled: bool}`
- live 且無 key → enabled=false；live 有 key → true；stub → true
"""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("AI_MODE", raising=False)
    from app.config import get_settings

    get_settings.cache_clear()


@pytest.fixture
async def auth(client):
    await client.post(
        "/api/auth/register",
        json={"email": "status@t.io", "username": "status_user", "password": "secret1234"},
    )
    r = await client.post(
        "/api/auth/login",
        json={"username": "status_user", "password": "secret1234"},
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def test_status_requires_auth(client):
    r = await client.get("/api/ai/status")
    assert r.status_code == 401


async def test_status_live_without_key(client, auth):
    r = await client.get("/api/ai/status", headers=auth)
    assert r.status_code == 200
    assert r.json() == {"mode": "live", "enabled": False}


async def test_status_live_with_key(client, auth, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    from app.config import get_settings

    get_settings.cache_clear()
    r = await client.get("/api/ai/status", headers=auth)
    assert r.status_code == 200
    assert r.json() == {"mode": "live", "enabled": True}


async def test_status_stub_mode(client, auth, monkeypatch):
    monkeypatch.setenv("AI_MODE", "stub")
    from app.config import get_settings

    get_settings.cache_clear()
    r = await client.get("/api/ai/status", headers=auth)
    assert r.status_code == 200
    assert r.json() == {"mode": "stub", "enabled": True}
