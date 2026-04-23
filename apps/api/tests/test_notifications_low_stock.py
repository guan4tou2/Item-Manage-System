from __future__ import annotations

import pytest


@pytest.fixture
async def auth(client):
    await client.post("/api/auth/register", json={
        "email": "ls@t.io", "username": "ls_user", "password": "secret1234",
    })
    r = await client.post("/api/auth/login", json={
        "username": "ls_user", "password": "secret1234",
    })
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _count_low_stock(client, auth) -> int:
    lst = (await client.get("/api/notifications", headers=auth)).json()
    return sum(1 for i in lst["items"] if i["type"] == "low_stock")


async def test_low_stock_fires_on_threshold_crossing(client, auth):
    create = await client.post(
        "/api/items", headers=auth, json={"name": "便當盒", "quantity": 5, "min_quantity": 2},
    )
    item_id = create.json()["id"]
    r = await client.patch(f"/api/items/{item_id}", headers=auth, json={"quantity": 1})
    assert r.status_code == 200
    assert await _count_low_stock(client, auth) == 1


async def test_low_stock_does_not_refire_while_below(client, auth):
    create = await client.post(
        "/api/items", headers=auth, json={"name": "牙刷", "quantity": 3, "min_quantity": 2},
    )
    item_id = create.json()["id"]
    await client.patch(f"/api/items/{item_id}", headers=auth, json={"quantity": 1})
    await client.patch(f"/api/items/{item_id}", headers=auth, json={"quantity": 0})
    assert await _count_low_stock(client, auth) == 1


async def test_low_stock_refires_after_refill(client, auth):
    create = await client.post(
        "/api/items", headers=auth, json={"name": "杯子", "quantity": 5, "min_quantity": 2},
    )
    item_id = create.json()["id"]
    await client.patch(f"/api/items/{item_id}", headers=auth, json={"quantity": 1})
    await client.patch(f"/api/items/{item_id}", headers=auth, json={"quantity": 5})
    await client.patch(f"/api/items/{item_id}", headers=auth, json={"quantity": 2})
    assert await _count_low_stock(client, auth) == 2


async def test_create_below_threshold_fires(client, auth):
    await client.post(
        "/api/items", headers=auth, json={"name": "襪子", "quantity": 1, "min_quantity": 2},
    )
    assert await _count_low_stock(client, auth) == 1


async def test_no_min_quantity_no_notification(client, auth):
    create = await client.post("/api/items", headers=auth, json={"name": "筷子", "quantity": 5})
    item_id = create.json()["id"]
    await client.patch(f"/api/items/{item_id}", headers=auth, json={"quantity": 0})
    assert await _count_low_stock(client, auth) == 0


async def test_changing_min_quantity_alone_does_not_fire(client, auth):
    create = await client.post(
        "/api/items", headers=auth, json={"name": "湯匙", "quantity": 3, "min_quantity": 1},
    )
    item_id = create.json()["id"]
    await client.patch(f"/api/items/{item_id}", headers=auth, json={"min_quantity": 5})
    assert await _count_low_stock(client, auth) == 0


async def test_low_stock_notification_has_link_to_item(client, auth):
    create = await client.post(
        "/api/items", headers=auth, json={"name": "牙膏", "quantity": 1, "min_quantity": 2},
    )
    item_id = create.json()["id"]
    lst = (await client.get("/api/notifications", headers=auth)).json()
    n = next(i for i in lst["items"] if i["type"] == "low_stock")
    assert n["link"] == f"/items/{item_id}"
    assert "牙膏" in n["title"]
