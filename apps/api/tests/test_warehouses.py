from __future__ import annotations
import pytest


@pytest.fixture
async def auth(client):
    await client.post("/api/auth/register", json={"email": "w@t.io", "username": "w_user", "password": "secret1234"})
    r = await client.post("/api/auth/login", json={"username": "w_user", "password": "secret1234"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def test_warehouse_crud(client, auth):
    r = await client.post("/api/warehouses", headers=auth, json={"name": "辦公室", "description": "總部"})
    assert r.status_code == 201
    wid = r.json()["id"]

    assert (await client.get("/api/warehouses", headers=auth)).status_code == 200

    r = await client.patch(f"/api/warehouses/{wid}", headers=auth, json={"name": "新辦公室"})
    assert r.json()["name"] == "新辦公室"

    assert (await client.delete(f"/api/warehouses/{wid}", headers=auth)).status_code == 204


async def test_item_assigned_to_warehouse(client, auth):
    w = (await client.post("/api/warehouses", headers=auth, json={"name": "家裡"})).json()
    item = (await client.post(
        "/api/items", headers=auth,
        json={"name": "筷子", "warehouse_id": w["id"]},
    )).json()
    assert item["warehouse_id"] == w["id"]

    # filter items by warehouse
    r = await client.get(f"/api/items?warehouse_id={w['id']}", headers=auth)
    assert r.json()["total"] == 1


async def test_warehouse_item_count(client, auth):
    w = (await client.post("/api/warehouses", headers=auth, json={"name": "X"})).json()
    await client.post("/api/items", headers=auth, json={"name": "A", "warehouse_id": w["id"]})
    await client.post("/api/items", headers=auth, json={"name": "B", "warehouse_id": w["id"]})
    detail = (await client.get(f"/api/warehouses/{w['id']}", headers=auth)).json()
    assert detail["item_count"] == 2


async def test_warehouse_duplicate_409(client, auth):
    await client.post("/api/warehouses", headers=auth, json={"name": "Dup"})
    r = await client.post("/api/warehouses", headers=auth, json={"name": "Dup"})
    assert r.status_code == 409
