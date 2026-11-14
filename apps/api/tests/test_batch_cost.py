"""Phase 49：批次成本、共用估值與既有數量流程的回歸。"""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4
import json

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.item_batch import ItemBatch
from app.models.item_history import QuantityLog
from app.models.item import Item
from app.models.user import User
from app.services import batches_service, reports_service, stats_service
from app.schemas.batch import BatchCreate, BatchUpdate
from pydantic import ValidationError


@pytest.fixture
async def auth(client):
    await client.post(
        "/api/auth/register",
        json={
            "email": "batchcost@t.io",
            "username": "batchcost",
            "password": "secret1234",
        },
    )
    login = await client.post(
        "/api/auth/login", json={"username": "batchcost", "password": "secret1234"}
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def make_item(client, auth, cost=None):
    r = await client.post(
        "/api/items",
        headers=auth,
        json={"name": "批次成本", "quantity": 4, "cost": cost},
    )
    assert r.status_code == 201
    return r.json()["id"]


async def add_batch(client, auth, item, cost=None, quantity=2, **extra):
    r = await client.post(
        f"/api/items/{item}/batches",
        headers=auth,
        json={"quantity": quantity, "unit_cost": cost, **extra},
    )
    assert r.status_code == 201
    return r.json()


@pytest.mark.parametrize("schema", [BatchCreate, BatchUpdate])
@pytest.mark.parametrize("value", ["-0.01", "1.234", "10000000000", "NaN", "Infinity"])
def test_cost_validation(schema, value):
    with pytest.raises(ValidationError):
        schema(unit_cost=value)


@pytest.mark.parametrize("value", [None, "0", "12.30", "9999999999.99"])
def test_cost_schema_accepts_boundaries(value):
    parsed = BatchCreate(unit_cost=value)
    assert parsed.unit_cost == (None if value is None else Decimal(value))


async def test_patch_omitted_preserves_and_null_clears(client, auth):
    item = await make_item(client, auth)
    batch = await add_batch(client, auth, item, "12.30")
    assert batch["unit_cost"] == "12.30"
    url = f"/api/items/{item}/batches/{batch['id']}"
    r = await client.patch(url, headers=auth, json={"note": "保留成本"})
    assert r.status_code == 200
    assert r.json()["unit_cost"] == "12.30"
    r = await client.patch(url, headers=auth, json={"unit_cost": "0"})
    assert r.json()["unit_cost"] == "0.00"
    r = await client.patch(url, headers=auth, json={"unit_cost": None})
    assert r.json()["unit_cost"] is None
    for method, path in [("post", f"/api/items/{item}/batches"), ("patch", url)]:
        for value in ["-1", "1.234"]:
            r = await getattr(client, method)(
                path, headers=auth, json={"unit_cost": value}
            )
            assert r.status_code == 422


@pytest.mark.parametrize(
    "default,costs,expected,unpriced",
    [
        ("10", ["2", "3"], "10.00", 0),
        ("10", ["2", None], "24.00", 0),
        ("10", [None, None], "40.00", 0),
        (None, [None, None], "0.00", 1),
        (None, ["2", None], "4.00", 1),
        (None, ["0", "3"], "6.00", 0),
    ],
)
async def test_valuation_combinations_and_distributions(
    client, auth, default, costs, expected, unpriced
):
    item = await make_item(client, auth, default)
    for cost in costs:
        await add_batch(client, auth, item, cost)
    body = (await client.get("/api/stats/value", headers=auth)).json()
    assert body["total_value"] == expected
    assert body["unpriced_items"] == unpriced
    assert body["priced_items"] == 1 - unpriced
    for key in ["by_category", "by_location", "by_warehouse"]:
        assert sum(Decimal(row["value"]) for row in body[key]) == Decimal(expected)
        assert sum(row["count"] for row in body[key]) == 1


async def test_fefo_depletion_and_disable(client, auth):
    item = await make_item(client, auth, "10")
    early = await add_batch(client, auth, item, "2", expiry_date="2026-01-01")
    late = await add_batch(client, auth, item, "5", expiry_date="2027-01-01")

    async def value():
        return (await client.get("/api/stats/value", headers=auth)).json()[
            "total_value"
        ]

    assert await value() == "14.00"
    r = await client.post(
        f"/api/items/{item}/consume", headers=auth, json={"quantity": 1}
    )
    assert r.status_code == 200
    assert await value() == "12.00"
    await client.post(f"/api/items/{item}/consume", headers=auth, json={"quantity": 1})
    assert await value() == "10.00"
    rows = (await client.get(f"/api/items/{item}/batches", headers=auth)).json()
    by_id = {b["id"]: b for b in rows}
    assert by_id[early["id"]]["unit_cost"] == "2.00"
    assert by_id[early["id"]]["is_depleted"] is True
    assert by_id[late["id"]]["unit_cost"] == "5.00"
    r = await client.post(f"/api/items/{item}/batches/disable", headers=auth)
    assert r.json()["quantity"] == 2
    assert r.json()["cost"] == "10.00"
    assert await value() == "20.00"
    assert (await client.get(f"/api/items/{item}/batches", headers=auth)).json() == []


async def test_no_active_batches_not_unpriced(client, auth):
    item = await make_item(client, auth)
    await add_batch(client, auth, item)
    await client.post(f"/api/items/{item}/consume", headers=auth, json={"quantity": 2})
    body = (await client.get("/api/stats/value", headers=auth)).json()
    assert body["unpriced_items"] == 0
    assert body["total_value"] == "0.00"


async def test_stocktake_preserves_cost_and_new_batch_falls_back(db_session):
    user = User(email="stockcost@t.io", username="stockcost", password_hash="unused")
    db_session.add(user)
    await db_session.flush()
    item = Item(
        owner_id=user.id,
        name="盤點",
        quantity=2,
        cost=Decimal("10"),
        track_batches=True,
    )
    db_session.add(item)
    await db_session.flush()
    batch = ItemBatch(item_id=item.id, quantity=2, unit_cost=Decimal("3"))
    db_session.add(batch)
    await db_session.commit()
    await batches_service.adjust_for_stocktake(
        db_session, user.id, item.id, stocktake_id=uuid4(), actual_quantity=1
    )
    await db_session.refresh(batch)
    assert batch.unit_cost == Decimal("3")
    assert (await stats_service.get_value(db_session, user.id)).total_value == Decimal(
        "3"
    )
    await batches_service.adjust_for_stocktake(
        db_session, user.id, item.id, stocktake_id=uuid4(), actual_quantity=4
    )
    rows = await batches_service.list_batches(db_session, user.id, item.id)
    assert sorted((b.quantity, b.unit_cost) for b in rows) == [
        (1, Decimal("3")),
        (3, None),
    ]
    assert (await stats_service.get_value(db_session, user.id)).total_value == Decimal(
        "33"
    )


@pytest.mark.parametrize("kind", ["monthly", "weekly"])
@pytest.mark.parametrize("quantity", [0, 4])
async def test_report_matches_stats_and_weighted_reconstruction(
    db_session, kind, quantity
):
    user = User(email="reportcost@t.io", username="reportcost", password_hash="unused")
    db_session.add(user)
    await db_session.flush()
    item = Item(
        owner_id=user.id,
        name="報表",
        quantity=quantity,
        cost=Decimal("7"),
        track_batches=True,
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
    )
    db_session.add(item)
    await db_session.flush()
    db_session.add_all(
        [
            ItemBatch(
                item_id=item.id,
                quantity=quantity // 2,
                unit_cost=Decimal("2"),
                is_depleted=quantity == 0,
            ),
            ItemBatch(
                item_id=item.id,
                quantity=quantity // 2,
                unit_cost=Decimal("5"),
                is_depleted=quantity == 0,
            ),
            QuantityLog(
                item_id=item.id,
                old_quantity=6,
                new_quantity=quantity,
                created_at=datetime(2026, 9, 15, tzinfo=UTC),
            ),
        ]
    )
    await db_session.commit()
    period = (
        reports_service.period_for(date(2026, 9, 1))
        if kind == "monthly"
        else reports_service.week_period(date(2026, 9, 14))
    )
    report = await reports_service.build_payload(
        db_session,
        user_id=user.id,
        period=period,
        generated_at=datetime(2026, 10, 1, tzinfo=UTC),
        currency="TWD",
        kind=kind,
    )
    stats = await stats_service.get_value(db_session, user.id)
    assert (
        Decimal(report.valuation.end)
        == stats.total_value
        == Decimal("14" if quantity else "0")
    )
    assert report.valuation.start == ("21.00" if quantity else "42.00")
    assert report.valuation.unpriced_items == stats.unpriced_items == 0
    assert report.version == 1


@pytest.mark.parametrize("legacy", [False, True])
async def test_backup_roundtrip_and_legacy(client, auth, legacy):
    item = await make_item(client, auth, "10")
    await add_batch(client, auth, item, "12.30")
    await add_batch(client, auth, item, "0")
    await add_batch(client, auth, item, None)
    doc = (await client.get("/api/backup/export", headers=auth)).json()
    assert [b["unit_cost"] for b in doc["item_batches"]] == ["12.30", "0.00", None]
    if legacy:
        for row in doc["item_batches"]:
            del row["unit_cost"]
    await client.post(
        "/api/auth/register",
        json={
            "email": "restore@t.io",
            "username": "restorecost",
            "password": "secret1234",
        },
    )
    login = await client.post(
        "/api/auth/login", json={"username": "restorecost", "password": "secret1234"}
    )
    other = {"Authorization": f"Bearer {login.json()['access_token']}"}
    r = await client.post(
        "/api/backup/import",
        headers=other,
        files={"file": ("backup.json", json.dumps(doc).encode(), "application/json")},
        data={"dry_run": "false"},
    )
    assert r.status_code == 200
    exported = (await client.get("/api/backup/export", headers=other)).json()
    assert exported["format_version"] == doc["format_version"]
    assert [b["unit_cost"] for b in exported["item_batches"]] == (
        [None] * 3 if legacy else ["12.30", "0.00", None]
    )
    expected = "60.00" if legacy else "44.60"
    assert (await client.get("/api/stats/value", headers=other)).json()[
        "total_value"
    ] == expected


async def test_database_rejects_negative_unit_cost(db_session):
    user = User(email="constraint@t.io", username="constraint", password_hash="unused")
    db_session.add(user)
    await db_session.flush()
    item = Item(owner_id=user.id, name="約束")
    db_session.add(item)
    await db_session.flush()
    db_session.add(ItemBatch(item_id=item.id, quantity=1, unit_cost=Decimal("-1")))
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


async def test_viewer_cannot_create_or_clear_cost(client, auth):
    item = await make_item(client, auth)
    batch = await add_batch(client, auth, item, "3")
    await client.post(
        "/api/auth/register",
        json={
            "email": "viewer@t.io",
            "username": "costviewer",
            "password": "secret1234",
        },
    )
    group = (
        await client.post("/api/groups", headers=auth, json={"name": "檢視者"})
    ).json()
    r = await client.post(
        f"/api/groups/{group['id']}/members",
        headers=auth,
        json={"username": "costviewer", "role": "viewer"},
    )
    assert r.status_code == 201
    login = await client.post(
        "/api/auth/login", json={"username": "costviewer", "password": "secret1234"}
    )
    viewer = {"Authorization": f"Bearer {login.json()['access_token']}"}
    r = await client.post(
        f"/api/items/{item}/batches",
        headers=viewer,
        json={"quantity": 1, "unit_cost": "5"},
    )
    assert r.status_code == 403
    r = await client.patch(
        f"/api/items/{item}/batches/{batch['id']}",
        headers=viewer,
        json={"unit_cost": None},
    )
    assert r.status_code == 403
    assert (await client.get(f"/api/items/{item}/batches", headers=auth)).json()[0][
        "unit_cost"
    ] == "3.00"
