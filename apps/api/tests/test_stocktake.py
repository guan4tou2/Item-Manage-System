from __future__ import annotations

from datetime import timedelta

import pytest

from app.clock import today_taipei


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


async def test_stocktake_tracked_positive_delta_creates_batch(client, auth):
    item = (
        await client.post("/api/items", headers=auth, json={"name": "T", "quantity": 5})
    ).json()
    setup = await client.post(f"/api/items/{item['id']}/batches", headers=auth, json={})
    assert setup.status_code == 201

    st = (
        await client.post("/api/stocktakes", headers=auth, json={"name": "批次盤點"})
    ).json()
    await client.post(
        f"/api/stocktakes/{st['id']}/scan",
        headers=auth,
        json={"item_id": item["id"], "actual_quantity": 8},
    )
    done = await client.post(f"/api/stocktakes/{st['id']}/complete", headers=auth)
    assert done.status_code == 200

    fresh = (await client.get(f"/api/items/{item['id']}", headers=auth)).json()
    assert fresh["quantity"] == 8

    batches = (
        await client.get(f"/api/items/{item['id']}/batches", headers=auth)
    ).json()
    assert len(batches) == 2
    added = next(b for b in batches if b["note"] and b["note"].startswith("stocktake:"))
    assert added["quantity"] == 3
    assert added["expiry_date"] is None
    assert sum(b["quantity"] for b in batches if not b["is_depleted"]) == 8

    logs = (
        await client.get(f"/api/items/{item['id']}/quantity-logs", headers=auth)
    ).json()
    assert any(
        "stocktake:" in (l.get("reason") or "")
        and l["old_quantity"] == 5
        and l["new_quantity"] == 8
        for l in logs
    )


async def test_stocktake_tracked_negative_delta_consumes_fefo(client, auth):
    item = (
        await client.post("/api/items", headers=auth, json={"name": "F", "quantity": 0})
    ).json()
    early = (
        await client.post(
            f"/api/items/{item['id']}/batches",
            headers=auth,
            json={
                "quantity": 2,
                "expiry_date": (today_taipei() + timedelta(days=3)).isoformat(),
            },
        )
    ).json()
    late = (
        await client.post(
            f"/api/items/{item['id']}/batches",
            headers=auth,
            json={
                "quantity": 3,
                "expiry_date": (today_taipei() + timedelta(days=30)).isoformat(),
            },
        )
    ).json()

    st = (
        await client.post("/api/stocktakes", headers=auth, json={"name": "批次盤點2"})
    ).json()
    await client.post(
        f"/api/stocktakes/{st['id']}/scan",
        headers=auth,
        json={"item_id": item["id"], "actual_quantity": 2},
    )
    done = await client.post(f"/api/stocktakes/{st['id']}/complete", headers=auth)
    assert done.status_code == 200

    fresh = (await client.get(f"/api/items/{item['id']}", headers=auth)).json()
    assert fresh["quantity"] == 2

    batches = (
        await client.get(f"/api/items/{item['id']}/batches", headers=auth)
    ).json()
    by_id = {b["id"]: b for b in batches}
    assert by_id[early["id"]]["is_depleted"] is True
    assert by_id[early["id"]]["quantity"] == 0
    assert by_id[late["id"]]["quantity"] == 2
    assert sum(b["quantity"] for b in batches if not b["is_depleted"]) == 2

    logs = (
        await client.get(f"/api/items/{item['id']}/quantity-logs", headers=auth)
    ).json()
    assert any(
        "stocktake:" in (l.get("reason") or "")
        and l["old_quantity"] == 5
        and l["new_quantity"] == 2
        for l in logs
    )
