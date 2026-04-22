import pytest


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
