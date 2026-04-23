from __future__ import annotations

import pytest


@pytest.fixture
async def auth(client):
    await client.post("/api/auth/register", json={
        "email": "n@t.io", "username": "n_user", "password": "secret1234",
    })
    r = await client.post("/api/auth/login", json={
        "username": "n_user", "password": "secret1234",
    })
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
async def other_auth(client):
    await client.post("/api/auth/register", json={
        "email": "o@t.io", "username": "o_user", "password": "secret1234",
    })
    r = await client.post("/api/auth/login", json={
        "username": "o_user", "password": "secret1234",
    })
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


class TestAuth:
    async def test_list_requires_auth(self, client):
        r = await client.get("/api/notifications")
        assert r.status_code == 401

    async def test_unread_count_requires_auth(self, client):
        r = await client.get("/api/notifications/unread-count")
        assert r.status_code == 401


class TestList:
    async def test_after_welcome_on_register(self, client, auth):
        r = await client.get("/api/notifications", headers=auth)
        body = r.json()
        assert body["total"] >= 1

    async def test_limit_validation_zero_rejected(self, client, auth):
        r = await client.get("/api/notifications?limit=0", headers=auth)
        assert r.status_code == 422

    async def test_limit_validation_too_large_rejected(self, client, auth):
        r = await client.get("/api/notifications?limit=200", headers=auth)
        assert r.status_code == 422


class TestUnreadCount:
    async def test_returns_int(self, client, auth):
        r = await client.get("/api/notifications/unread-count", headers=auth)
        assert r.status_code == 200
        assert isinstance(r.json()["count"], int)


class TestMarkRead:
    async def test_marks_own_notification(self, client, auth):
        lst = (await client.get("/api/notifications", headers=auth)).json()
        if not lst["items"]:
            pytest.skip("welcome not yet wired")
        nid = lst["items"][0]["id"]
        r = await client.patch(f"/api/notifications/{nid}/read", headers=auth)
        assert r.status_code == 200
        assert r.json()["read_at"] is not None

    async def test_other_owner_returns_404(self, client, auth, other_auth):
        other_list = (await client.get("/api/notifications", headers=other_auth)).json()
        if not other_list["items"]:
            pytest.skip("welcome not yet wired")
        nid = other_list["items"][0]["id"]
        r = await client.patch(f"/api/notifications/{nid}/read", headers=auth)
        assert r.status_code == 404


class TestMarkAllRead:
    async def test_returns_marked_count(self, client, auth):
        r = await client.post("/api/notifications/mark-all-read", headers=auth)
        assert r.status_code == 200
        assert "marked" in r.json()


class TestDelete:
    async def test_delete_own_204(self, client, auth):
        lst = (await client.get("/api/notifications", headers=auth)).json()
        if not lst["items"]:
            pytest.skip("welcome not yet wired")
        nid = lst["items"][0]["id"]
        r = await client.delete(f"/api/notifications/{nid}", headers=auth)
        assert r.status_code == 204

    async def test_delete_other_owner_404(self, client, auth, other_auth):
        other_list = (await client.get("/api/notifications", headers=other_auth)).json()
        if not other_list["items"]:
            pytest.skip("welcome not yet wired")
        nid = other_list["items"][0]["id"]
        r = await client.delete(f"/api/notifications/{nid}", headers=auth)
        assert r.status_code == 404
