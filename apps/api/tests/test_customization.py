from __future__ import annotations
import pytest


@pytest.fixture
async def auth(client):
    await client.post("/api/auth/register", json={"email": "c@t.io", "username": "c_user", "password": "secret1234"})
    r = await client.post("/api/auth/login", json={"username": "c_user", "password": "secret1234"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# item types
async def test_item_type_crud(client, auth):
    r = await client.post("/api/item-types", headers=auth, json={"name": "電器"})
    assert r.status_code == 201
    assert r.json()["name"] == "電器"
    lst = await client.get("/api/item-types", headers=auth)
    assert len(lst.json()) == 1
    d = await client.delete(f"/api/item-types/{r.json()['id']}", headers=auth)
    assert d.status_code == 204


async def test_item_type_duplicate_409(client, auth):
    await client.post("/api/item-types", headers=auth, json={"name": "X"})
    r = await client.post("/api/item-types", headers=auth, json={"name": "X"})
    assert r.status_code == 409


# custom fields
async def test_custom_field_crud(client, auth):
    r = await client.post("/api/custom-fields", headers=auth, json={"name": "保固期限", "field_type": "date"})
    assert r.status_code == 201
    field_id = r.json()["id"]
    assert (await client.get("/api/custom-fields", headers=auth)).status_code == 200
    assert (await client.delete(f"/api/custom-fields/{field_id}", headers=auth)).status_code == 204


async def test_custom_field_invalid_type_422(client, auth):
    r = await client.post("/api/custom-fields", headers=auth, json={"name": "x", "field_type": "weird"})
    assert r.status_code == 422


# custom values on items
async def test_item_custom_values(client, auth):
    item = (await client.post("/api/items", headers=auth, json={"name": "wrench"})).json()
    field = (await client.post("/api/custom-fields", headers=auth, json={"name": "serial", "field_type": "text"})).json()
    r = await client.post(
        f"/api/items/{item['id']}/custom-values", headers=auth,
        json={"custom_field_id": field["id"], "value": "SN-123"},
    )
    assert r.status_code == 200
    assert r.json()["value"] == "SN-123"

    listed = await client.get(f"/api/items/{item['id']}/custom-values", headers=auth)
    assert listed.status_code == 200
    assert len(listed.json()) == 1


# templates
async def test_template_crud(client, auth):
    r = await client.post(
        "/api/item-templates", headers=auth,
        json={"name": "標準螺絲", "payload": {"name": "M4x10", "quantity": 50}},
    )
    assert r.status_code == 201
    tid = r.json()["id"]
    assert (await client.get("/api/item-templates", headers=auth)).status_code == 200
    assert (await client.delete(f"/api/item-templates/{tid}", headers=auth)).status_code == 204
