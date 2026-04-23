from __future__ import annotations
import pytest


@pytest.fixture
async def auth(client):
    await client.post("/api/auth/register", json={"email": "ln@t.io", "username": "ln_user", "password": "secret1234"})
    r = await client.post("/api/auth/login", json={"username": "ln_user", "password": "secret1234"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
async def item_id(client, auth):
    r = await client.post("/api/items", headers=auth, json={"name": "傘"})
    return r.json()["id"]


async def test_empty_history(client, auth, item_id):
    r = await client.get(f"/api/items/{item_id}/loans", headers=auth)
    assert r.status_code == 200
    assert r.json() == []


async def test_create_with_label(client, auth, item_id):
    r = await client.post(
        f"/api/items/{item_id}/loans", headers=auth, json={"borrower_label": "張三"},
    )
    assert r.status_code == 201
    assert r.json()["borrower_label"] == "張三"


async def test_active_uniqueness(client, auth, item_id):
    await client.post(f"/api/items/{item_id}/loans", headers=auth, json={"borrower_label": "a"})
    r = await client.post(f"/api/items/{item_id}/loans", headers=auth, json={"borrower_label": "b"})
    assert r.status_code == 409


async def test_return(client, auth, item_id):
    loan = (await client.post(f"/api/items/{item_id}/loans", headers=auth, json={"borrower_label": "a"})).json()
    r = await client.post(f"/api/items/{item_id}/loans/{loan['id']}/return", headers=auth)
    assert r.status_code == 200
    assert r.json()["returned_at"] is not None


async def test_delete(client, auth, item_id):
    loan = (await client.post(f"/api/items/{item_id}/loans", headers=auth, json={"borrower_label": "a"})).json()
    r = await client.delete(f"/api/items/{item_id}/loans/{loan['id']}", headers=auth)
    assert r.status_code == 204
