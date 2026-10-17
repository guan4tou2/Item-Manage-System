from __future__ import annotations

from decimal import Decimal

import pytest

from app.auth.password import hash_password
from app.models.user import User
from app.services import stats_service


@pytest.fixture
async def auth(client):
    await client.post(
        "/api/auth/register",
        json={"email": "sv@t.io", "username": "stats_value_user", "password": "secret1234"},
    )
    r = await client.post(
        "/api/auth/login",
        json={"username": "stats_value_user", "password": "secret1234"},
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def test_requires_auth(client):
    r = await client.get("/api/stats/value")
    assert r.status_code == 401


async def test_empty_db(client, auth):
    r = await client.get("/api/stats/value", headers=auth)
    assert r.status_code == 200
    assert r.json() == {
        "currency": "TWD",
        "total_value": "0.00",
        "priced_items": 0,
        "unpriced_items": 0,
        "total_items": 0,
        "by_category": [],
        "by_location": [],
        "by_warehouse": [],
    }


async def test_totals_weighted_by_quantity_and_unpriced(client, auth):
    await client.post(
        "/api/items", headers=auth, json={"name": "a", "quantity": 3, "cost": "10.00"}
    )
    await client.post("/api/items", headers=auth, json={"name": "b", "quantity": 1})
    body = (await client.get("/api/stats/value", headers=auth)).json()
    assert body["total_value"] == "30.00"
    assert body["priced_items"] == 1
    assert body["unpriced_items"] == 1
    assert body["total_items"] == 2


async def test_by_category_splits_and_counts(client, auth):
    cat = (
        await client.post("/api/categories", headers=auth, json={"name": "咖啡"})
    ).json()
    await client.post(
        "/api/items",
        headers=auth,
        json={"name": "a", "quantity": 2, "cost": "5.25", "category_id": cat["id"]},
    )
    await client.post("/api/items", headers=auth, json={"name": "b", "quantity": 1})
    buckets = (await client.get("/api/stats/value", headers=auth)).json()["by_category"]
    by_id = {b["category_id"]: b for b in buckets}
    assert by_id[cat["id"]] == {
        "category_id": cat["id"],
        "name": "咖啡",
        "value": "10.50",
        "count": 1,
    }
    assert by_id[None] == {
        "category_id": None,
        "name": None,
        "value": "0.00",
        "count": 1,
    }


async def test_by_location_uses_tree_path_label(client, auth):
    root = (
        await client.post("/api/locations", headers=auth, json={"name": "1F"})
    ).json()
    child = (
        await client.post(
            "/api/locations",
            headers=auth,
            json={"name": "廚房", "parent_id": root["id"]},
        )
    ).json()
    await client.post(
        "/api/items",
        headers=auth,
        json={"name": "a", "quantity": 1, "cost": "2.50", "location_id": child["id"]},
    )
    buckets = (await client.get("/api/stats/value", headers=auth)).json()["by_location"]
    assert len(buckets) == 1
    assert buckets[0] == {
        "location_id": child["id"],
        "label": "1F / 廚房",
        "value": "2.50",
        "count": 1,
    }


async def test_by_warehouse_buckets(client, auth):
    wh = (await client.post("/api/warehouses", headers=auth, json={"name": "倉A"})).json()
    await client.post("/api/items", headers=auth, json={"name": "a", "cost": "1.00"})
    await client.post(
        "/api/items",
        headers=auth,
        json={"name": "b", "cost": "3.00", "warehouse_id": wh["id"]},
    )
    buckets = (await client.get("/api/stats/value", headers=auth)).json()["by_warehouse"]
    by_id = {b["warehouse_id"]: b for b in buckets}
    assert by_id[wh["id"]]["value"] == "3.00"
    assert by_id[wh["id"]]["name"] == "倉A"
    assert by_id[wh["id"]]["count"] == 1
    assert by_id[None]["value"] == "1.00"


async def test_currency_follows_preference(client, auth):
    await client.put(
        "/api/users/me/preferences", headers=auth, json={"currency": "JPY"}
    )
    body = (await client.get("/api/stats/value", headers=auth)).json()
    assert body["currency"] == "JPY"


async def test_deleted_items_excluded(client, auth):
    item = (
        await client.post("/api/items", headers=auth, json={"name": "a", "cost": "5.00"})
    ).json()
    await client.delete(f"/api/items/{item['id']}", headers=auth)
    body = (await client.get("/api/stats/value", headers=auth)).json()
    assert body["total_value"] == "0.00"
    assert body["total_items"] == 0


async def test_cross_owner_isolation(client, auth):
    await client.post(
        "/api/auth/register",
        json={"email": "other@t.io", "username": "sv_other", "password": "secret1234"},
    )
    other = (
        await client.post(
            "/api/auth/login",
            json={"username": "sv_other", "password": "secret1234"},
        )
    ).json()
    other_h = {"Authorization": f"Bearer {other['access_token']}"}
    await client.post(
        "/api/items", headers=other_h, json={"name": "theirs", "cost": "99.99"}
    )
    await client.post("/api/items", headers=auth, json={"name": "mine", "cost": "1.00"})
    body = (await client.get("/api/stats/value", headers=auth)).json()
    assert body["total_value"] == "1.00"
    assert body["total_items"] == 1


async def test_unknown_stored_currency_falls_back_to_twd(db_session):
    user = User(
        email="cur@t.io",
        username="cur_user",
        password_hash=hash_password("secret1234"),
        preferences={"currency": "XYZ"},
    )
    db_session.add(user)
    await db_session.commit()

    result = await stats_service.get_value(db_session, user.id)
    assert result.currency == "TWD"
    assert result.total_value == Decimal("0.00")
