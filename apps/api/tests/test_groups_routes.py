from __future__ import annotations
import pytest


@pytest.fixture
async def auth(client):
    await client.post("/api/auth/register", json={"email": "g@t.io", "username": "g_user", "password": "secret1234"})
    r = await client.post("/api/auth/login", json={"username": "g_user", "password": "secret1234"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
async def friend_auth(client):
    await client.post("/api/auth/register", json={"email": "fr@t.io", "username": "fr_user", "password": "secret1234"})
    r = await client.post("/api/auth/login", json={"username": "fr_user", "password": "secret1234"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def test_requires_auth(client):
    assert (await client.get("/api/groups")).status_code == 401


async def test_crud_roundtrip(client, auth):
    r = await client.post("/api/groups", headers=auth, json={"name": "g"})
    assert r.status_code == 201
    gid = r.json()["id"]
    assert (await client.get(f"/api/groups/{gid}", headers=auth)).status_code == 200
    assert (await client.patch(f"/api/groups/{gid}", headers=auth, json={"name": "new"})).json()["name"] == "new"
    assert (await client.delete(f"/api/groups/{gid}", headers=auth)).status_code == 204


async def test_add_and_remove_member(client, auth, friend_auth):
    gid = (await client.post("/api/groups", headers=auth, json={"name": "fam"})).json()["id"]
    r = await client.post(f"/api/groups/{gid}/members", headers=auth, json={"username": "fr_user"})
    assert r.status_code == 201
    member_user_id = r.json()["user_id"]
    assert (await client.delete(f"/api/groups/{gid}/members/{member_user_id}", headers=auth)).status_code == 204


async def test_add_member_unknown_404(client, auth):
    gid = (await client.post("/api/groups", headers=auth, json={"name": "g"})).json()["id"]
    r = await client.post(f"/api/groups/{gid}/members", headers=auth, json={"username": "ghost"})
    assert r.status_code == 404


async def test_add_duplicate_member_409(client, auth):
    gid = (await client.post("/api/groups", headers=auth, json={"name": "g"})).json()["id"]
    r = await client.post(f"/api/groups/{gid}/members", headers=auth, json={"username": "g_user"})
    assert r.status_code == 409


async def test_cross_owner_404(client, auth, friend_auth):
    gid = (await client.post("/api/groups", headers=auth, json={"name": "g"})).json()["id"]
    assert (await client.get(f"/api/groups/{gid}", headers=friend_auth)).status_code == 404
