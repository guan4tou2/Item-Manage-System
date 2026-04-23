from __future__ import annotations
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
async def auth(client):
    await client.post("/api/auth/register", json={"email": "wh@t.io", "username": "wh_user", "password": "secret1234"})
    r = await client.post("/api/auth/login", json={"username": "wh_user", "password": "secret1234"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def test_webhook_crud(client, auth):
    r = await client.post(
        "/api/webhooks", headers=auth,
        json={"name": "test", "url": "http://example.com/hook", "events": ["item.created"]},
    )
    assert r.status_code == 201
    wid = r.json()["id"]

    listed = await client.get("/api/webhooks", headers=auth)
    assert len(listed.json()) == 1

    r = await client.patch(f"/api/webhooks/{wid}", headers=auth, json={"is_active": False})
    assert r.json()["is_active"] is False

    assert (await client.delete(f"/api/webhooks/{wid}", headers=auth)).status_code == 204


async def test_webhook_dispatch_on_item_create(client, auth, monkeypatch):
    # Mock httpx to avoid actual network
    class MockResponse:
        def __init__(self):
            self.status_code = 200
            self.text = "OK"

    mock_post = AsyncMock(return_value=MockResponse())
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = mock_post

    import httpx
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: mock_client)

    await client.post(
        "/api/webhooks", headers=auth,
        json={"name": "t", "url": "http://example.com/hook"},
    )
    await client.post("/api/items", headers=auth, json={"name": "X"})
    # Webhook was fired
    assert mock_post.called


async def test_webhook_deliveries_log(client, auth, monkeypatch):
    class MockResponse:
        def __init__(self):
            self.status_code = 201
            self.text = "created"

    mock_post = AsyncMock(return_value=MockResponse())
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = mock_post

    import httpx
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: mock_client)

    wh = (await client.post(
        "/api/webhooks", headers=auth,
        json={"name": "t", "url": "http://example.com/hook"},
    )).json()
    await client.post("/api/items", headers=auth, json={"name": "A"})

    deliveries = (await client.get(f"/api/webhooks/{wh['id']}/deliveries", headers=auth)).json()
    assert len(deliveries) >= 1
    assert deliveries[0]["event"] == "item.created"
    assert deliveries[0]["status_code"] == 201
