from __future__ import annotations
import pytest


@pytest.fixture
async def auth(client):
    await client.post("/api/auth/register", json={"email": "h@t.io", "username": "h_user", "password": "secret1234"})
    r = await client.post("/api/auth/login", json={"username": "h_user", "password": "secret1234"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def test_quantity_log_on_update(client, auth):
    item = (await client.post("/api/items", headers=auth, json={"name": "x", "quantity": 5})).json()
    await client.patch(f"/api/items/{item['id']}", headers=auth, json={"quantity": 3})
    logs = (await client.get(f"/api/items/{item['id']}/quantity-logs", headers=auth)).json()
    assert len(logs) == 1
    assert logs[0]["old_quantity"] == 5
    assert logs[0]["new_quantity"] == 3


async def test_version_on_update(client, auth):
    item = (await client.post("/api/items", headers=auth, json={"name": "before"})).json()
    await client.patch(f"/api/items/{item['id']}", headers=auth, json={"name": "after"})
    versions = (await client.get(f"/api/items/{item['id']}/versions", headers=auth)).json()
    assert len(versions) == 1
    assert versions[0]["snapshot"]["name"] == "before"


async def test_no_log_when_quantity_unchanged(client, auth):
    item = (await client.post("/api/items", headers=auth, json={"name": "x", "quantity": 5})).json()
    await client.patch(f"/api/items/{item['id']}", headers=auth, json={"name": "rename"})
    logs = (await client.get(f"/api/items/{item['id']}/quantity-logs", headers=auth)).json()
    assert len(logs) == 0
