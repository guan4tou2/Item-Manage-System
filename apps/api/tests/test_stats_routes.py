from datetime import timedelta

import pytest

from app.clock import today_taipei


@pytest.fixture
async def auth(client):
    await client.post("/api/auth/register", json={
        "email": "s@t.io", "username": "stats_user", "password": "secret1234",
    })
    r = await client.post("/api/auth/login", json={
        "username": "stats_user", "password": "secret1234",
    })
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


class TestStatsAuth:
    async def test_overview_requires_auth(self, client):
        r = await client.get("/api/stats/overview")
        assert r.status_code == 401


class TestOverview:
    async def test_empty(self, client, auth):
        r = await client.get("/api/stats/overview", headers=auth)
        assert r.status_code == 200
        assert r.json() == {
            "total_items": 0, "total_quantity": 0,
            "total_categories": 0, "total_locations": 0, "total_tags": 0,
            "total_warehouses": 0, "low_stock_items": 0, "active_loans": 0,
        }

    async def test_counts(self, client, auth):
        await client.post("/api/items", headers=auth, json={"name": "a", "quantity": 3})
        await client.post("/api/items", headers=auth, json={"name": "b", "quantity": 2, "tag_names": ["x"]})
        r = await client.get("/api/stats/overview", headers=auth)
        body = r.json()
        assert body["total_items"] == 2
        assert body["total_quantity"] == 5
        assert body["total_tags"] == 1


class TestByCategory:
    async def test_includes_uncategorized_bucket(self, client, auth):
        cat = await client.post("/api/categories", headers=auth, json={"name": "gadgets"})
        cat_id = cat.json()["id"]
        await client.post("/api/items", headers=auth, json={"name": "p", "category_id": cat_id})
        await client.post("/api/items", headers=auth, json={"name": "q"})
        r = await client.get("/api/stats/by-category", headers=auth)
        assert r.status_code == 200
        rows = r.json()
        ids = {row["category_id"] for row in rows}
        assert cat_id in ids
        assert None in ids


class TestByLocation:
    async def test_label_format(self, client, auth):
        loc = await client.post(
            "/api/locations", headers=auth,
            json={"floor": "1F", "room": "客廳", "zone": None},
        )
        lid = loc.json()["id"]
        await client.post("/api/items", headers=auth, json={"name": "p", "location_id": lid})
        r = await client.get("/api/stats/by-location", headers=auth)
        assert r.status_code == 200
        row = next(x for x in r.json() if x["location_id"] == lid)
        assert row["label"] == "1F / 客廳"


class TestByTag:
    async def test_default_limit_and_order(self, client, auth):
        await client.post("/api/items", headers=auth, json={"name": "a", "tag_names": ["red", "blue"]})
        await client.post("/api/items", headers=auth, json={"name": "b", "tag_names": ["red"]})
        r = await client.get("/api/stats/by-tag", headers=auth)
        assert r.status_code == 200
        rows = r.json()
        assert rows[0]["name"] == "red"
        assert rows[0]["count"] == 2

    async def test_limit_query_validation(self, client, auth):
        r = await client.get("/api/stats/by-tag?limit=51", headers=auth)
        assert r.status_code == 422
        r = await client.get("/api/stats/by-tag?limit=0", headers=auth)
        assert r.status_code == 422


class TestRecent:
    async def test_order_and_default_limit(self, client, auth):
        for i in range(7):
            await client.post("/api/items", headers=auth, json={"name": f"item{i}"})
        r = await client.get("/api/stats/recent", headers=auth)
        assert r.status_code == 200
        names = [i["name"] for i in r.json()]
        assert names[0] == "item6"
        assert len(names) == 5

    async def test_custom_limit(self, client, auth):
        for i in range(3):
            await client.post("/api/items", headers=auth, json={"name": f"x{i}"})
        r = await client.get("/api/stats/recent?limit=2", headers=auth)
        assert len(r.json()) == 2

    async def test_limit_validation(self, client, auth):
        r = await client.get("/api/stats/recent?limit=21", headers=auth)
        assert r.status_code == 422


class TestExpiry:
    async def _tracked(self, client, auth, *, name: str, days: int | None) -> str:
        item = (
            await client.post(
                "/api/items", headers=auth, json={"name": name, "quantity": 1}
            )
        ).json()
        body: dict = {}
        if days is not None:
            body["expiry_date"] = (today_taipei() + timedelta(days=days)).isoformat()
        resp = await client.post(
            f"/api/items/{item['id']}/batches", headers=auth, json=body
        )
        assert resp.status_code == 201, resp.text
        return item["id"]

    async def test_empty(self, client, auth):
        r = await client.get("/api/stats/expiry", headers=auth)
        assert r.status_code == 200
        assert r.json() == {
            "expired_count": 0,
            "expiring_count": 0,
            "reminded_today": False,
            "items": [],
        }

    async def test_counts_and_order(self, client, auth):
        await self._tracked(client, auth, name="過期", days=-1)
        soon_id = await self._tracked(client, auth, name="快了", days=3)
        await self._tracked(client, auth, name="遠", days=40)
        await self._tracked(client, auth, name="無期", days=None)

        body = (await client.get("/api/stats/expiry", headers=auth)).json()

        assert body["expired_count"] == 1
        assert body["expiring_count"] == 1
        assert [i["name"] for i in body["items"]] == ["過期", "快了"]
        assert body["items"][0]["status"] == "expired"
        assert body["items"][0]["days_left"] == -1
        assert body["items"][1]["status"] == "expiring"
        assert body["items"][1]["item_id"] == soon_id

    async def test_days_window(self, client, auth):
        await self._tracked(client, auth, name="三天", days=3)

        r = await client.get("/api/stats/expiry?days=2", headers=auth)
        assert r.json()["expiring_count"] == 0
        assert r.json()["items"] == []

        r = await client.get("/api/stats/expiry?days=3", headers=auth)
        assert r.json()["expiring_count"] == 1
        assert r.json()["items"][0]["name"] == "三天"

    async def test_days_bounds(self, client, auth):
        assert (
            await client.get("/api/stats/expiry?days=1", headers=auth)
        ).status_code == 200
        assert (
            await client.get("/api/stats/expiry?days=365", headers=auth)
        ).status_code == 200
        assert (
            await client.get("/api/stats/expiry?days=0", headers=auth)
        ).status_code == 422
        assert (
            await client.get("/api/stats/expiry?days=366", headers=auth)
        ).status_code == 422

    async def test_items_capped_at_10(self, client, auth):
        for i in range(12):
            await self._tracked(client, auth, name=f"i{i:02d}", days=1 + i)

        body = (await client.get("/api/stats/expiry", headers=auth)).json()

        assert body["expiring_count"] == 12
        assert len(body["items"]) == 10
        assert body["items"][0]["name"] == "i00"
