from __future__ import annotations
import pytest


@pytest.fixture
async def auth(client):
    await client.post("/api/auth/register", json={"email": "t@t.io", "username": "t_user", "password": "secret1234"})
    r = await client.post("/api/auth/login", json={"username": "t_user", "password": "secret1234"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def test_create_list_delete_token(client, auth):
    r = await client.post("/api/users/me/tokens", headers=auth, json={"name": "CI"})
    assert r.status_code == 201
    body = r.json()
    assert body["token"].startswith("ims_pat_")
    assert body["name"] == "CI"
    token_id = body["id"]

    listed = await client.get("/api/users/me/tokens", headers=auth)
    assert len(listed.json()) == 1

    d = await client.delete(f"/api/users/me/tokens/{token_id}", headers=auth)
    assert d.status_code == 204


async def test_pat_authenticates(client, auth):
    created = (await client.post("/api/users/me/tokens", headers=auth, json={"name": "api"})).json()
    pat_headers = {"Authorization": f"Bearer {created['token']}"}
    r = await client.get("/api/users/me", headers=pat_headers)
    assert r.status_code == 200
    assert r.json()["username"] == "t_user"


async def test_pat_invalid_401(client):
    r = await client.get("/api/users/me", headers={"Authorization": "Bearer ims_pat_invalid"})
    assert r.status_code == 401
