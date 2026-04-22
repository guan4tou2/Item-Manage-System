import pytest

from app.models.tag import Tag


@pytest.fixture
async def auth_setup(client):
    await client.post("/api/auth/register", json={
        "email": "tag@t.io", "username": "tag_user", "password": "secret1234",
    })
    resp = await client.post("/api/auth/login", json={
        "username": "tag_user", "password": "secret1234",
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestTagsList:
    async def test_empty(self, client, auth_setup):
        resp = await client.get("/api/tags", headers=auth_setup)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_unauthenticated_401(self, client):
        assert (await client.get("/api/tags")).status_code == 401
