import pytest


@pytest.fixture
async def auth_headers(client):
    await client.post("/api/auth/register", json={
        "email": "items@t.io", "username": "items_user", "password": "secret1234",
    })
    resp = await client.post("/api/auth/login", json={
        "username": "items_user", "password": "secret1234",
    })
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


class TestItemCreate:
    async def test_minimal(self, client, auth_headers):
        resp = await client.post("/api/items", headers=auth_headers, json={"name": "thing"})
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "thing"
        assert body["quantity"] == 1
        assert body["tags"] == []

    async def test_with_tags_autocreates(self, client, auth_headers):
        resp = await client.post(
            "/api/items", headers=auth_headers,
            json={"name": "x", "tag_names": ["a", "B", "a"]},
        )
        assert resp.status_code == 201
        assert sorted(t["name"] for t in resp.json()["tags"]) == ["a", "b"]
        tags = await client.get("/api/tags", headers=auth_headers)
        assert sorted(t["name"] for t in tags.json()) == ["a", "b"]

    async def test_missing_name_422(self, client, auth_headers):
        resp = await client.post("/api/items", headers=auth_headers, json={})
        assert resp.status_code == 422

    async def test_unauthenticated_401(self, client):
        resp = await client.post("/api/items", json={"name": "x"})
        assert resp.status_code == 401


class TestItemList:
    async def test_empty(self, client, auth_headers):
        resp = await client.get("/api/items", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body == {"items": [], "total": 0, "page": 1, "per_page": 20}

    async def test_search_q(self, client, auth_headers):
        await client.post("/api/items", headers=auth_headers, json={"name": "apple"})
        await client.post("/api/items", headers=auth_headers, json={"name": "banana"})
        resp = await client.get("/api/items?q=app", headers=auth_headers)
        assert [i["name"] for i in resp.json()["items"]] == ["apple"]

    async def test_filter_tags(self, client, auth_headers):
        await client.post("/api/items", headers=auth_headers, json={"name": "a", "tag_names": ["red"]})
        await client.post("/api/items", headers=auth_headers, json={"name": "b", "tag_names": ["blue"]})
        tags = (await client.get("/api/tags", headers=auth_headers)).json()
        red_id = next(t["id"] for t in tags if t["name"] == "red")
        resp = await client.get(f"/api/items?tag_ids={red_id}", headers=auth_headers)
        assert [i["name"] for i in resp.json()["items"]] == ["a"]

    async def test_pagination_metadata(self, client, auth_headers):
        for i in range(3):
            await client.post("/api/items", headers=auth_headers, json={"name": f"n{i}"})
        resp = await client.get("/api/items?per_page=2", headers=auth_headers)
        body = resp.json()
        assert body["total"] == 3
        assert body["page"] == 1
        assert body["per_page"] == 2
        assert len(body["items"]) == 2


class TestItemGet:
    async def test_not_found_404(self, client, auth_headers):
        resp = await client.get(
            "/api/items/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_other_user_404(self, client):
        await client.post("/api/auth/register", json={
            "email": "a@t.io", "username": "usr_a", "password": "secret1234"})
        tok_a = (await client.post("/api/auth/login", json={
            "username": "usr_a", "password": "secret1234"})).json()["access_token"]
        created = await client.post(
            "/api/items",
            headers={"Authorization": f"Bearer {tok_a}"},
            json={"name": "only a"},
        )
        item_id = created.json()["id"]
        await client.post("/api/auth/register", json={
            "email": "b@t.io", "username": "usr_b", "password": "secret1234"})
        tok_b = (await client.post("/api/auth/login", json={
            "username": "usr_b", "password": "secret1234"})).json()["access_token"]
        resp = await client.get(
            f"/api/items/{item_id}",
            headers={"Authorization": f"Bearer {tok_b}"},
        )
        assert resp.status_code == 404


class TestItemUpdate:
    async def test_patch_name(self, client, auth_headers):
        created = (await client.post(
            "/api/items", headers=auth_headers, json={"name": "old"}
        )).json()
        resp = await client.patch(
            f"/api/items/{created['id']}", headers=auth_headers,
            json={"name": "new"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "new"

    async def test_patch_replaces_tags(self, client, auth_headers):
        created = (await client.post(
            "/api/items", headers=auth_headers,
            json={"name": "x", "tag_names": ["a"]},
        )).json()
        resp = await client.patch(
            f"/api/items/{created['id']}", headers=auth_headers,
            json={"tag_names": ["b", "c"]},
        )
        assert sorted(t["name"] for t in resp.json()["tags"]) == ["b", "c"]


class TestItemDelete:
    async def test_soft_delete(self, client, auth_headers):
        created = (await client.post(
            "/api/items", headers=auth_headers, json={"name": "x"}
        )).json()
        resp = await client.delete(f"/api/items/{created['id']}", headers=auth_headers)
        assert resp.status_code == 204
        get_resp = await client.get(f"/api/items/{created['id']}", headers=auth_headers)
        assert get_resp.status_code == 404
        list_resp = await client.get("/api/items", headers=auth_headers)
        assert list_resp.json()["total"] == 0
