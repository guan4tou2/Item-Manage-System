from __future__ import annotations


async def test_register_creates_welcome_notification(client):
    await client.post("/api/auth/register", json={
        "email": "w@t.io", "username": "w_user", "password": "secret1234",
    })
    r = await client.post("/api/auth/login", json={
        "username": "w_user", "password": "secret1234",
    })
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    lst = (await client.get("/api/notifications", headers=headers)).json()
    assert lst["total"] == 1
    assert lst["unread_count"] == 1
    item = lst["items"][0]
    assert item["type"] == "system.welcome"
    assert item["title"] == "歡迎使用 IMS"
    assert item["link"] == "/dashboard"
    assert item["read_at"] is None
