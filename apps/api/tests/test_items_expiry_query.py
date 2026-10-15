from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import event

from app.clock import today_taipei


def _days_from_today(days: int) -> str:
    return (today_taipei() + timedelta(days=days)).isoformat()


@pytest.fixture
async def auth_headers(client):
    await client.post("/api/auth/register", json={
        "email": "expiry@t.io", "username": "expiry_user", "password": "secret1234",
    })
    resp = await client.post("/api/auth/login", json={
        "username": "expiry_user", "password": "secret1234",
    })
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
async def select_counter(test_engine):
    statements: list[str] = []

    def _before_execute(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith(("SELECT", "WITH")):
            statements.append(statement)

    event.listen(test_engine.sync_engine, "before_cursor_execute", _before_execute)
    yield statements
    event.remove(test_engine.sync_engine, "before_cursor_execute", _before_execute)


async def _seed_item(client, headers, *, name: str = "牛奶", expiry: str | None = None) -> str:
    item = (
        await client.post(
            "/api/items", headers=headers, json={"name": name, "quantity": 1}
        )
    ).json()
    body: dict = {}
    if expiry is not None:
        body["expiry_date"] = expiry
    resp = await client.post(
        f"/api/items/{item['id']}/batches", headers=headers, json=body
    )
    assert resp.status_code == 201, resp.text
    return item["id"]


async def _names(client, headers, params: str = "") -> list[str]:
    resp = await client.get(f"/api/items{params}", headers=headers)
    assert resp.status_code == 200
    return [i["name"] for i in resp.json()["items"]]


class TestListEnrichment:
    async def test_tracked_item_exposes_soonest_expiry(self, client, auth_headers):
        await _seed_item(client, auth_headers, expiry=_days_from_today(5))

        row = (await client.get("/api/items", headers=auth_headers)).json()["items"][0]

        assert row["track_batches"] is True
        assert row["soonest_expiry"] == _days_from_today(5)

    async def test_untracked_item_has_no_soonest_expiry(self, client, auth_headers):
        await client.post(
            "/api/items", headers=auth_headers, json={"name": "筆", "quantity": 3}
        )

        row = (await client.get("/api/items", headers=auth_headers)).json()["items"][0]

        assert row["track_batches"] is False
        assert row["soonest_expiry"] is None

    async def test_soonest_expiry_ignores_depleted_batches(self, client, auth_headers):
        item_id = await _seed_item(client, auth_headers, expiry=_days_from_today(1))
        far = (
            await client.post(
                f"/api/items/{item_id}/batches",
                headers=auth_headers,
                json={"quantity": 1, "expiry_date": _days_from_today(30)},
            )
        ).json()
        listed = (
            await client.get(f"/api/items/{item_id}/batches", headers=auth_headers)
        ).json()
        near = next(b for b in listed if b["id"] != far["id"])
        resp = await client.post(
            f"/api/items/{item_id}/batches/{near['id']}/consume",
            headers=auth_headers,
            json={"quantity": 1},
        )
        assert resp.status_code == 200

        row = (await client.get("/api/items", headers=auth_headers)).json()["items"][0]

        assert row["soonest_expiry"] == _days_from_today(30)


class TestExpiryFilterAndSort:
    async def test_filters(self, client, auth_headers):
        await _seed_item(client, auth_headers, name="過期", expiry=_days_from_today(-1))
        await _seed_item(client, auth_headers, name="快了", expiry=_days_from_today(3))
        await _seed_item(client, auth_headers, name="遠", expiry=_days_from_today(30))
        await _seed_item(client, auth_headers, name="無期")

        assert await _names(client, auth_headers, "?expiry=expired") == ["過期"]
        assert await _names(client, auth_headers, "?expiry=expiring_soon") == ["快了"]
        assert await _names(client, auth_headers, "?sort=expiry_asc") == [
            "過期",
            "快了",
            "遠",
            "無期",
        ]

    async def test_multi_batch_filter_uses_min_expiry(self, client, auth_headers):
        item_id = await _seed_item(client, auth_headers, name="混", expiry=_days_from_today(-2))
        await client.post(
            f"/api/items/{item_id}/batches",
            headers=auth_headers,
            json={"quantity": 1, "expiry_date": _days_from_today(2)},
        )

        # MIN 為過期 → 屬 expired，不屬 expiring_soon
        assert await _names(client, auth_headers, "?expiry=expiring_soon") == []
        assert await _names(client, auth_headers, "?expiry=expired") == ["混"]

    async def test_invalid_filter_is_422(self, client, auth_headers):
        resp = await client.get("/api/items?expiry=bogus", headers=auth_headers)
        assert resp.status_code == 422


class TestTrackedQuantityGuard:
    async def test_patch_quantity_on_tracked_item_is_409(self, client, auth_headers):
        item_id = await _seed_item(client, auth_headers)

        resp = await client.patch(
            f"/api/items/{item_id}", headers=auth_headers, json={"quantity": 3}
        )
        assert resp.status_code == 409

    async def test_patch_other_fields_on_tracked_item_still_works(self, client, auth_headers):
        item_id = await _seed_item(client, auth_headers)

        resp = await client.patch(
            f"/api/items/{item_id}", headers=auth_headers, json={"name": "改名"}
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "改名"


class TestQueryCount:
    async def test_list_query_count_is_flat(self, client, auth_headers, select_counter):
        for i in range(3):
            await _seed_item(client, auth_headers, name=f"小{i}", expiry=_days_from_today(5 + i))
        select_counter.clear()
        assert (
            await client.get("/api/items?per_page=50", headers=auth_headers)
        ).status_code == 200
        small = len(select_counter)

        for i in range(27):
            await _seed_item(client, auth_headers, name=f"大{i}", expiry=_days_from_today(5))
        select_counter.clear()
        resp = await client.get("/api/items?per_page=50", headers=auth_headers)
        assert resp.json()["total"] == 30
        large = len(select_counter)

        assert large == small, f"query count grew with row count: {small} → {large}"
