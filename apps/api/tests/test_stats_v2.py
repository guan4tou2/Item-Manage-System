from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest


@pytest.fixture
async def auth(client):
    await client.post(
        "/api/auth/register",
        json={"email": "sv2@t.io", "username": "stats_v2_user", "password": "secret1234"},
    )
    r = await client.post(
        "/api/auth/login",
        json={"username": "stats_v2_user", "password": "secret1234"},
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ---- /api/stats/overview expanded fields --------------------------------


async def test_overview_includes_new_zero_fields(client, auth):
    r = await client.get("/api/stats/overview", headers=auth)
    body = r.json()
    assert body["total_warehouses"] == 0
    assert body["low_stock_items"] == 0
    assert body["active_loans"] == 0


async def test_overview_counts_low_stock_and_active_loans(client, auth):
    # create two items: one low, one not
    low = await client.post(
        "/api/items",
        headers=auth,
        json={"name": "low", "quantity": 1, "min_quantity": 5},
    )
    assert low.status_code == 201
    await client.post(
        "/api/items",
        headers=auth,
        json={"name": "ok", "quantity": 10, "min_quantity": 2},
    )
    # third item has no min_quantity — should never count
    await client.post(
        "/api/items",
        headers=auth,
        json={"name": "no-min", "quantity": 0},
    )

    # open a loan on the low-stock item
    await client.post(
        f"/api/items/{low.json()['id']}/loans",
        headers=auth,
        json={"borrower_label": "alice"},
    )

    # warehouse count
    await client.post("/api/warehouses", headers=auth, json={"name": "W1"})

    r = await client.get("/api/stats/overview", headers=auth)
    body = r.json()
    assert body["low_stock_items"] == 1
    assert body["active_loans"] == 1
    assert body["total_warehouses"] == 1


# ---- /api/stats/by-warehouse -------------------------------------------


async def test_by_warehouse_splits_assigned_and_unassigned(client, auth):
    wh = (await client.post("/api/warehouses", headers=auth, json={"name": "wh-a"})).json()
    await client.post(
        "/api/items", headers=auth, json={"name": "assigned", "warehouse_id": wh["id"]}
    )
    await client.post("/api/items", headers=auth, json={"name": "unassigned"})
    r = await client.get("/api/stats/by-warehouse", headers=auth)
    buckets = r.json()
    by_id = {b["warehouse_id"]: b for b in buckets}
    assert by_id[wh["id"]]["count"] == 1
    assert by_id[wh["id"]]["name"] == "wh-a"
    assert None in by_id
    assert by_id[None]["count"] == 1
    assert by_id[None]["name"] is None


# ---- /api/stats/low-stock ----------------------------------------------


async def test_low_stock_lists_only_deficit_items(client, auth):
    deficit = await client.post(
        "/api/items",
        headers=auth,
        json={"name": "bolts", "quantity": 2, "min_quantity": 10},
    )
    await client.post(
        "/api/items",
        headers=auth,
        json={"name": "nuts", "quantity": 20, "min_quantity": 5},
    )
    r = await client.get("/api/stats/low-stock", headers=auth)
    rows = r.json()
    assert len(rows) == 1
    row = rows[0]
    assert row["item_id"] == deficit.json()["id"]
    assert row["quantity"] == 2
    assert row["min_quantity"] == 10
    assert row["deficit"] == 8


async def test_low_stock_orders_by_deficit_desc(client, auth):
    await client.post(
        "/api/items",
        headers=auth,
        json={"name": "small", "quantity": 4, "min_quantity": 5},
    )
    await client.post(
        "/api/items",
        headers=auth,
        json={"name": "huge", "quantity": 1, "min_quantity": 100},
    )
    r = await client.get("/api/stats/low-stock", headers=auth)
    rows = r.json()
    assert [row["name"] for row in rows] == ["huge", "small"]


# ---- /api/stats/active-loans -------------------------------------------


async def test_active_loans_returns_only_unreturned(client, auth):
    item = await client.post("/api/items", headers=auth, json={"name": "lamp"})
    item_id = item.json()["id"]
    loan = (
        await client.post(
            f"/api/items/{item_id}/loans",
            headers=auth,
            json={"borrower_label": "bob", "expected_return": "2099-01-01"},
        )
    ).json()

    r = await client.get("/api/stats/active-loans", headers=auth)
    rows = r.json()
    assert len(rows) == 1
    assert rows[0]["loan_id"] == loan["id"]
    assert rows[0]["borrower_label"] == "bob"
    assert rows[0]["is_overdue"] is False

    # return the loan → should drop out
    await client.post(
        f"/api/items/{item_id}/loans/{loan['id']}/return", headers=auth
    )
    r2 = await client.get("/api/stats/active-loans", headers=auth)
    assert r2.json() == []


async def test_active_loans_flags_overdue(client, auth):
    item = (await client.post("/api/items", headers=auth, json={"name": "x"})).json()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    await client.post(
        f"/api/items/{item['id']}/loans",
        headers=auth,
        json={"borrower_label": "c", "expected_return": yesterday},
    )
    r = await client.get("/api/stats/active-loans", headers=auth)
    rows = r.json()
    assert len(rows) == 1
    assert rows[0]["is_overdue"] is True


# ---- /api/stats/trend --------------------------------------------------


async def test_trend_returns_dense_series(client, auth):
    r = await client.get("/api/stats/trend?days=7", headers=auth)
    rows = r.json()
    assert len(rows) == 7
    # days should be consecutive and ascending
    days = [date.fromisoformat(p["day"]) for p in rows]
    for earlier, later in zip(days, days[1:]):
        assert (later - earlier).days == 1
    # no items created yet → all counts zero
    assert all(p["count"] == 0 for p in rows)


async def test_trend_counts_new_items_today(client, auth):
    await client.post("/api/items", headers=auth, json={"name": "today"})
    r = await client.get("/api/stats/trend?days=1", headers=auth)
    rows = r.json()
    assert len(rows) == 1
    assert rows[0]["count"] == 1


# ---- /api/stats/activity -----------------------------------------------


async def test_activity_merges_quantity_and_loan_events(client, auth):
    item = (
        await client.post(
            "/api/items", headers=auth, json={"name": "foo", "quantity": 1}
        )
    ).json()

    # trigger quantity log via PATCH
    await client.patch(
        f"/api/items/{item['id']}", headers=auth, json={"quantity": 5}
    )

    # trigger a loan event
    await client.post(
        f"/api/items/{item['id']}/loans",
        headers=auth,
        json={"borrower_label": "dave"},
    )

    r = await client.get("/api/stats/activity", headers=auth)
    rows = r.json()
    kinds = {row["kind"] for row in rows}
    assert "quantity" in kinds
    assert "loan_out" in kinds
    # every row has a summary string
    for row in rows:
        assert row["summary"]
        assert row["at"]


async def test_activity_respects_limit(client, auth):
    item = (await client.post("/api/items", headers=auth, json={"name": "a"})).json()
    for q in range(2, 6):
        await client.patch(
            f"/api/items/{item['id']}", headers=auth, json={"quantity": q}
        )
    r = await client.get("/api/stats/activity?limit=2", headers=auth)
    assert len(r.json()) == 2


# ---- auth ---------------------------------------------------------------


async def test_all_new_endpoints_require_auth(client):
    for path in [
        "/api/stats/by-warehouse",
        "/api/stats/low-stock",
        "/api/stats/active-loans",
        "/api/stats/trend",
        "/api/stats/activity",
    ]:
        r = await client.get(path)
        assert r.status_code == 401, path
