import pytest


@pytest.fixture
async def auth_headers(client):
    """Register + login, return Bearer auth headers."""
    await client.post(
        "/api/auth/register",
        json={
            "email": "prefs@example.com",
            "username": "prefs_user",
            "password": "secret1234",
        },
    )
    resp = await client.post(
        "/api/auth/login",
        json={"username": "prefs_user", "password": "secret1234"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestGetPreferences:
    async def test_unauthenticated_returns_401(self, client):
        resp = await client.get("/api/users/me/preferences")
        assert resp.status_code == 401

    async def test_returns_default_theme(self, client, auth_headers):
        resp = await client.get(
            "/api/users/me/preferences", headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json() == {"theme": "system"}


class TestPutPreferences:
    async def test_unauthenticated_returns_401(self, client):
        resp = await client.put(
            "/api/users/me/preferences", json={"theme": "dark"}
        )
        assert resp.status_code == 401

    async def test_updates_theme(self, client, auth_headers):
        resp = await client.put(
            "/api/users/me/preferences",
            headers=auth_headers,
            json={"theme": "dark"},
        )
        assert resp.status_code == 200
        assert resp.json()["theme"] == "dark"

    async def test_merge_preserves_other_keys(self, client, auth_headers):
        await client.put(
            "/api/users/me/preferences",
            headers=auth_headers,
            json={"theme": "dark", "language": "zh-TW"},
        )
        resp = await client.put(
            "/api/users/me/preferences",
            headers=auth_headers,
            json={"theme": "light"},
        )
        body = resp.json()
        assert body["theme"] == "light"
        assert body["language"] == "zh-TW"

    async def test_invalid_theme_returns_422(self, client, auth_headers):
        resp = await client.put(
            "/api/users/me/preferences",
            headers=auth_headers,
            json={"theme": "neon"},
        )
        assert resp.status_code == 422
