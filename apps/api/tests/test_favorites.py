from __future__ import annotations
import pytest


@pytest.fixture
async def auth(client):
    await client.post("/api/auth/register", json={"email": "f@t.io", "username": "f_user", "password": "secret1234"})
    r = await client.post("/api/auth/login", json={"username": "f_user", "password": "secret1234"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def test_toggle_favorite(client, auth):
    item = (await client.post("/api/items", headers=auth, json={"name": "X"})).json()
    assert item["is_favorite"] is False
    r = await client.post(f"/api/items/{item['id']}/favorite", headers=auth)
    assert r.status_code == 200
    assert r.json()["is_favorite"] is True
    r = await client.post(f"/api/items/{item['id']}/favorite", headers=auth)
    assert r.json()["is_favorite"] is False


async def test_filter_favorite(client, auth):
    a = (await client.post("/api/items", headers=auth, json={"name": "A"})).json()
    b = (await client.post("/api/items", headers=auth, json={"name": "B"})).json()
    await client.post(f"/api/items/{a['id']}/favorite", headers=auth)
    r = await client.get("/api/items?favorite=true", headers=auth)
    names = [i["name"] for i in r.json()["items"]]
    assert "A" in names
    assert "B" not in names


async def test_favorite_non_owner_404(client, auth):
    await client.post("/api/auth/register", json={"email": "o@t.io", "username": "o_user", "password": "secret1234"})
    r = await client.post("/api/auth/login", json={"username": "o_user", "password": "secret1234"})
    other_headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    item = (await client.post("/api/items", headers=other_headers, json={"name": "X"})).json()
    r = await client.post(f"/api/items/{item['id']}/favorite", headers=auth)
    assert r.status_code == 404
