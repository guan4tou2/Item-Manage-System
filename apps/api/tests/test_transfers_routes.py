from __future__ import annotations
import pytest


@pytest.fixture
async def two_auths(client):
    await client.post("/api/auth/register", json={"email": "a@t.io", "username": "a_user", "password": "secret1234"})
    await client.post("/api/auth/register", json={"email": "b@t.io", "username": "b_user", "password": "secret1234"})
    ra = await client.post("/api/auth/login", json={"username": "a_user", "password": "secret1234"})
    rb = await client.post("/api/auth/login", json={"username": "b_user", "password": "secret1234"})
    return (
        {"Authorization": f"Bearer {ra.json()['access_token']}"},
        {"Authorization": f"Bearer {rb.json()['access_token']}"},
    )


async def test_requires_auth(client):
    assert (await client.get("/api/transfers")).status_code == 401


async def test_create_and_accept(client, two_auths):
    a, b = two_auths
    item_id = (await client.post("/api/items", headers=a, json={"name": "X"})).json()["id"]
    t = (await client.post("/api/transfers", headers=a, json={"item_id": item_id, "to_username": "b_user"})).json()
    assert t["status"] == "pending"
    r = await client.post(f"/api/transfers/{t['id']}/accept", headers=b)
    assert r.status_code == 200
    assert r.json()["status"] == "accepted"
    got = (await client.get(f"/api/items/{item_id}", headers=b)).json()
    assert got["owner_username"] == "b_user"


async def test_self_transfer_422(client, two_auths):
    a, _ = two_auths
    item_id = (await client.post("/api/items", headers=a, json={"name": "X"})).json()["id"]
    r = await client.post("/api/transfers", headers=a, json={"item_id": item_id, "to_username": "a_user"})
    assert r.status_code == 422


async def test_non_owner_cannot_create(client, two_auths):
    a, b = two_auths
    item_id = (await client.post("/api/items", headers=a, json={"name": "X"})).json()["id"]
    r = await client.post("/api/transfers", headers=b, json={"item_id": item_id, "to_username": "a_user"})
    assert r.status_code == 404


async def test_reject(client, two_auths):
    a, b = two_auths
    item_id = (await client.post("/api/items", headers=a, json={"name": "X"})).json()["id"]
    t = (await client.post("/api/transfers", headers=a, json={"item_id": item_id, "to_username": "b_user"})).json()
    r = await client.post(f"/api/transfers/{t['id']}/reject", headers=b)
    assert r.status_code == 200
    assert r.json()["status"] == "rejected"


async def test_cancel(client, two_auths):
    a, b = two_auths
    item_id = (await client.post("/api/items", headers=a, json={"name": "X"})).json()["id"]
    t = (await client.post("/api/transfers", headers=a, json={"item_id": item_id, "to_username": "b_user"})).json()
    r = await client.post(f"/api/transfers/{t['id']}/cancel", headers=a)
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"


async def test_notification_emitted_to_recipient(client, two_auths):
    a, b = two_auths
    item_id = (await client.post("/api/items", headers=a, json={"name": "X"})).json()["id"]
    await client.post("/api/transfers", headers=a, json={"item_id": item_id, "to_username": "b_user"})
    notifs = (await client.get("/api/notifications", headers=b)).json()
    types = [n["type"] for n in notifs["items"]]
    assert "transfer.request" in types
