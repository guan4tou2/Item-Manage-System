from __future__ import annotations
import pytest


@pytest.fixture
async def auth(client):
    await client.post("/api/auth/register", json={"email": "b@t.io", "username": "b_user", "password": "secret1234"})
    r = await client.post("/api/auth/login", json={"username": "b_user", "password": "secret1234"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def test_export_empty(client, auth):
    r = await client.get("/api/backup/export", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["format_version"] == 1
    assert body["items"] == []
    assert body["categories"] == []
    assert "Content-Disposition" in r.headers
    assert "attachment" in r.headers["Content-Disposition"]


async def test_export_includes_items(client, auth):
    await client.post("/api/items", headers=auth, json={"name": "A", "quantity": 3, "tag_names": ["x"]})
    body = (await client.get("/api/backup/export", headers=auth)).json()
    assert len(body["items"]) == 1
    assert body["items"][0]["name"] == "A"
    assert body["items"][0]["tag_names"] == ["x"]


async def test_export_includes_lists(client, auth):
    lst = (await client.post("/api/lists", headers=auth, json={"kind": "generic", "title": "test"})).json()
    await client.post(f"/api/lists/{lst['id']}/entries", headers=auth, json={"name": "a"})
    body = (await client.get("/api/backup/export", headers=auth)).json()
    assert len(body["lists"]) == 1
    assert len(body["lists"][0]["entries"]) == 1


async def test_export_includes_warehouses(client, auth):
    await client.post("/api/warehouses", headers=auth, json={"name": "家裡"})
    body = (await client.get("/api/backup/export", headers=auth)).json()
    assert len(body["warehouses"]) == 1
