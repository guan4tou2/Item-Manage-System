import pytest


@pytest.fixture
async def auth_headers(client):
    await client.post("/api/auth/register", json={
        "email": "cat@t.io", "username": "cat_user", "password": "secret1234",
    })
    resp = await client.post("/api/auth/login", json={
        "username": "cat_user", "password": "secret1234",
    })
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


class TestCategories:
    async def test_list_empty(self, client, auth_headers):
        resp = await client.get("/api/categories", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_create_and_list_tree(self, client, auth_headers):
        parent = await client.post("/api/categories", headers=auth_headers, json={"name": "tools"})
        assert parent.status_code == 201
        child = await client.post("/api/categories", headers=auth_headers,
                                  json={"name": "hammers", "parent_id": parent.json()["id"]})
        assert child.status_code == 201
        resp = await client.get("/api/categories", headers=auth_headers)
        tree = resp.json()
        assert len(tree) == 1
        assert tree[0]["name"] == "tools"
        assert len(tree[0]["children"]) == 1
        assert tree[0]["children"][0]["name"] == "hammers"

    async def test_invalid_parent_returns_422(self, client, auth_headers):
        resp = await client.post("/api/categories", headers=auth_headers,
                                 json={"name": "x", "parent_id": 9999})
        assert resp.status_code == 422

    async def test_update_name(self, client, auth_headers):
        created = await client.post("/api/categories", headers=auth_headers, json={"name": "a"})
        cid = created.json()["id"]
        resp = await client.patch(f"/api/categories/{cid}", headers=auth_headers, json={"name": "b"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "b"

    async def test_update_cycle_rejected(self, client, auth_headers):
        parent = (await client.post("/api/categories", headers=auth_headers, json={"name": "p"})).json()
        child = (await client.post("/api/categories", headers=auth_headers,
                                   json={"name": "c", "parent_id": parent["id"]})).json()
        resp = await client.patch(f"/api/categories/{parent['id']}", headers=auth_headers,
                                  json={"parent_id": child["id"]})
        assert resp.status_code == 422

    async def test_update_self_parent_rejected(self, client, auth_headers):
        cat = (await client.post("/api/categories", headers=auth_headers, json={"name": "x"})).json()
        resp = await client.patch(
            f"/api/categories/{cat['id']}",
            headers=auth_headers,
            json={"parent_id": cat["id"]},
        )
        assert resp.status_code == 422

    async def test_other_user_cannot_delete(self, client):
        await client.post("/api/auth/register", json={
            "email": "d_a@t.io", "username": "del_a", "password": "secret1234"})
        tok_a = (await client.post("/api/auth/login", json={
            "username": "del_a", "password": "secret1234"})).json()["access_token"]
        await client.post("/api/auth/register", json={
            "email": "d_b@t.io", "username": "del_b", "password": "secret1234"})
        tok_b = (await client.post("/api/auth/login", json={
            "username": "del_b", "password": "secret1234"})).json()["access_token"]
        created = await client.post(
            "/api/categories",
            headers={"Authorization": f"Bearer {tok_a}"},
            json={"name": "a-only"},
        )
        cid = created.json()["id"]
        resp = await client.delete(
            f"/api/categories/{cid}",
            headers={"Authorization": f"Bearer {tok_b}"},
        )
        assert resp.status_code == 404

    async def test_delete_clears_children_parent(self, client, auth_headers):
        parent = (await client.post("/api/categories", headers=auth_headers, json={"name": "p"})).json()
        child = (await client.post("/api/categories", headers=auth_headers,
                                   json={"name": "c", "parent_id": parent["id"]})).json()
        del_resp = await client.delete(f"/api/categories/{parent['id']}", headers=auth_headers)
        assert del_resp.status_code == 204
        tree = (await client.get("/api/categories", headers=auth_headers)).json()
        names = [n["name"] for n in tree]
        assert "c" in names
        assert "p" not in names
        child_node = next(n for n in tree if n["name"] == "c")
        assert child_node["parent_id"] is None

    async def test_unauthenticated_401(self, client):
        assert (await client.get("/api/categories")).status_code == 401

    async def test_other_user_cannot_access(self, client):
        await client.post("/api/auth/register", json={
            "email": "a@t.io", "username": "user_a", "password": "secret1234"})
        tok_a = (await client.post("/api/auth/login", json={
            "username": "user_a", "password": "secret1234"})).json()["access_token"]
        await client.post("/api/auth/register", json={
            "email": "b@t.io", "username": "user_b", "password": "secret1234"})
        tok_b = (await client.post("/api/auth/login", json={
            "username": "user_b", "password": "secret1234"})).json()["access_token"]
        created = await client.post(
            "/api/categories",
            headers={"Authorization": f"Bearer {tok_a}"},
            json={"name": "only-a"},
        )
        cid = created.json()["id"]
        resp = await client.patch(
            f"/api/categories/{cid}",
            headers={"Authorization": f"Bearer {tok_b}"},
            json={"name": "hijacked"},
        )
        assert resp.status_code == 404
