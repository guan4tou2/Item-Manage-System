from __future__ import annotations
import pytest


@pytest.fixture
async def auth(client):
    await client.post("/api/auth/register", json={"email": "ch@t.io", "username": "ch_user", "password": "secret1234"})
    r = await client.post("/api/auth/login", json={"username": "ch_user", "password": "secret1234"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def test_status_default_unconfigured(client, auth):
    r = await client.get("/api/channels/status", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["email_configured"] is False
    assert body["user_line_linked"] is False
    assert body["user_web_push_count"] == 0


async def test_line_link_roundtrip(client, auth):
    r = await client.put("/api/channels/line", headers=auth, json={"line_user_id": "U1234567"})
    assert r.status_code == 204
    status = (await client.get("/api/channels/status", headers=auth)).json()
    assert status["user_line_linked"] is True
    r = await client.delete("/api/channels/line", headers=auth)
    assert r.status_code == 204
    status = (await client.get("/api/channels/status", headers=auth)).json()
    assert status["user_line_linked"] is False


async def test_telegram_link_roundtrip(client, auth):
    r = await client.put("/api/channels/telegram", headers=auth, json={"chat_id": "12345"})
    assert r.status_code == 204


async def test_web_push_sub_roundtrip(client, auth):
    sub = (await client.post(
        "/api/channels/web-push/subscriptions", headers=auth,
        json={"endpoint": "https://fcm.googleapis.com/x", "p256dh": "AAA", "auth": "BBB"},
    )).json()
    listed = await client.get("/api/channels/web-push/subscriptions", headers=auth)
    assert len(listed.json()) == 1
    r = await client.delete(f"/api/channels/web-push/subscriptions/{sub['id']}", headers=auth)
    assert r.status_code == 204


async def test_test_send_email_without_config_fails(client, auth):
    r = await client.post("/api/channels/test/email", headers=auth)
    # email not configured → deliver_email returns False → {"delivered": False}
    assert r.status_code == 200
    assert r.json() == {"delivered": False}
