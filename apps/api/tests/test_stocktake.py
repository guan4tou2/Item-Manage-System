from __future__ import annotations
import pytest


@pytest.fixture
async def auth(client):
    await client.post("/api/auth/register", json={"email": "s@t.io", "username": "s_user", "password": "secret1234"})
    r = await client.post("/api/auth/login", json={"username": "s_user", "password": "secret1234"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def test_full_stocktake_flow(client, auth):
    # Create items
    a = (await client.post("/api/items", headers=auth, json={"name": "A", "quantity": 10})).json()
    b = (await client.post("/api/items", headers=auth, json={"name": "B", "quantity": 5})).json()

    # Start stocktake
    st = (await client.post("/api/stocktakes", headers=auth, json={"name": "Q1 盤點"})).json()
    assert st["status"] == "open"
    sid = st["id"]

    # Scan: A actual=8, B actual=5 (match)
    await client.post(f"/api/stocktakes/{sid}/scan", headers=auth, json={"item_id": a["id"], "actual_quantity": 8})
    await client.post(f"/api/stocktakes/{sid}/scan", headers=auth, json={"item_id": b["id"], "actual_quantity": 5})

    # Get detail — discrepancy 1
    detail = (await client.get(f"/api/stocktakes/{sid}", headers=auth)).json()
    assert detail["item_count"] == 2
    assert detail["discrepancy_count"] == 1

    # Complete — applies deltas
    completed = (await client.post(f"/api/stocktakes/{sid}/complete", headers=auth)).json()
    assert completed["status"] == "completed"

    # Verify A now has quantity 8 and a quantity log
    fresh_a = (await client.get(f"/api/items/{a['id']}", headers=auth)).json()
    assert fresh_a["quantity"] == 8
    logs = (await client.get(f"/api/items/{a['id']}/quantity-logs", headers=auth)).json()
    assert any(l["old_quantity"] == 10 and l["new_quantity"] == 8 for l in logs)


async def test_stocktake_cancel(client, auth):
    st = (await client.post("/api/stocktakes", headers=auth, json={"name": "cancelled"})).json()
    r = await client.post(f"/api/stocktakes/{st['id']}/cancel", headers=auth)
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"


async def test_scan_on_closed_stocktake_409(client, auth):
    item = (await client.post("/api/items", headers=auth, json={"name": "X"})).json()
    st = (await client.post("/api/stocktakes", headers=auth, json={"name": "closed"})).json()
    await client.post(f"/api/stocktakes/{st['id']}/cancel", headers=auth)
    r = await client.post(
        f"/api/stocktakes/{st['id']}/scan", headers=auth,
        json={"item_id": item["id"], "actual_quantity": 1},
    )
    assert r.status_code == 409
