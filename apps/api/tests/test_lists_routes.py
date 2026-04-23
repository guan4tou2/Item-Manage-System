from __future__ import annotations

import pytest


@pytest.fixture
async def auth(client):
    await client.post("/api/auth/register", json={
        "email": "L@t.io", "username": "L_user", "password": "secret1234",
    })
    r = await client.post("/api/auth/login", json={
        "username": "L_user", "password": "secret1234",
    })
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
async def other_auth(client):
    await client.post("/api/auth/register", json={
        "email": "O@t.io", "username": "O_user", "password": "secret1234",
    })
    r = await client.post("/api/auth/login", json={
        "username": "O_user", "password": "secret1234",
    })
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


class TestAuth:
    async def test_list_requires_auth(self, client):
        r = await client.get("/api/lists")
        assert r.status_code == 401


class TestListCRUD:
    async def test_empty_index(self, client, auth):
        r = await client.get("/api/lists", headers=auth)
        assert r.status_code == 200
        assert r.json() == {"items": [], "total": 0}

    async def test_create_and_fetch(self, client, auth):
        c = await client.post(
            "/api/lists", headers=auth,
            json={"kind": "travel", "title": "T"},
        )
        assert c.status_code == 201
        list_id = c.json()["id"]
        g = await client.get(f"/api/lists/{list_id}", headers=auth)
        assert g.status_code == 200
        assert g.json()["entries"] == []

    async def test_create_rejects_unknown_kind(self, client, auth):
        r = await client.post("/api/lists", headers=auth, json={"kind": "weird", "title": "x"})
        assert r.status_code == 422

    async def test_create_rejects_date_order(self, client, auth):
        r = await client.post(
            "/api/lists", headers=auth,
            json={"kind": "travel", "title": "T", "start_date": "2026-05-10", "end_date": "2026-05-01"},
        )
        assert r.status_code == 422

    async def test_kind_filter(self, client, auth):
        await client.post("/api/lists", headers=auth, json={"kind": "travel", "title": "T"})
        await client.post("/api/lists", headers=auth, json={"kind": "shopping", "title": "S"})
        r = await client.get("/api/lists?kind=travel", headers=auth)
        body = r.json()
        assert body["total"] == 1
        assert body["items"][0]["kind"] == "travel"

    async def test_update_list(self, client, auth):
        c = await client.post("/api/lists", headers=auth, json={"kind": "generic", "title": "old"})
        list_id = c.json()["id"]
        r = await client.patch(f"/api/lists/{list_id}", headers=auth, json={"title": "new"})
        assert r.status_code == 200
        assert r.json()["title"] == "new"

    async def test_delete_list(self, client, auth):
        c = await client.post("/api/lists", headers=auth, json={"kind": "generic", "title": "x"})
        list_id = c.json()["id"]
        d = await client.delete(f"/api/lists/{list_id}", headers=auth)
        assert d.status_code == 204

    async def test_cross_owner_404(self, client, auth, other_auth):
        c = await client.post("/api/lists", headers=other_auth, json={"kind": "generic", "title": "other"})
        list_id = c.json()["id"]
        r = await client.get(f"/api/lists/{list_id}", headers=auth)
        assert r.status_code == 404

    async def test_limit_validation(self, client, auth):
        r = await client.get("/api/lists?limit=0", headers=auth)
        assert r.status_code == 422


class TestEntries:
    async def _make_list(self, client, auth) -> str:
        r = await client.post("/api/lists", headers=auth, json={"kind": "generic", "title": "x"})
        return r.json()["id"]

    async def test_create_entry(self, client, auth):
        lid = await self._make_list(client, auth)
        r = await client.post(
            f"/api/lists/{lid}/entries", headers=auth, json={"name": "牙刷"},
        )
        assert r.status_code == 201
        assert r.json()["position"] == 0
        assert r.json()["is_done"] is False

    async def test_toggle_entry(self, client, auth):
        lid = await self._make_list(client, auth)
        e = (await client.post(
            f"/api/lists/{lid}/entries", headers=auth, json={"name": "a"}
        )).json()
        t = await client.post(
            f"/api/lists/{lid}/entries/{e['id']}/toggle", headers=auth,
        )
        assert t.status_code == 200
        assert t.json()["is_done"] is True

    async def test_update_entry(self, client, auth):
        lid = await self._make_list(client, auth)
        e = (await client.post(
            f"/api/lists/{lid}/entries", headers=auth, json={"name": "a"}
        )).json()
        u = await client.patch(
            f"/api/lists/{lid}/entries/{e['id']}", headers=auth,
            json={"name": "b", "quantity": 3},
        )
        assert u.status_code == 200
        body = u.json()
        assert body["name"] == "b"
        assert body["quantity"] == 3

    async def test_delete_entry(self, client, auth):
        lid = await self._make_list(client, auth)
        e = (await client.post(
            f"/api/lists/{lid}/entries", headers=auth, json={"name": "a"}
        )).json()
        d = await client.delete(
            f"/api/lists/{lid}/entries/{e['id']}", headers=auth,
        )
        assert d.status_code == 204

    async def test_reorder_entries(self, client, auth):
        lid = await self._make_list(client, auth)
        a = (await client.post(
            f"/api/lists/{lid}/entries", headers=auth, json={"name": "a"}
        )).json()
        b = (await client.post(
            f"/api/lists/{lid}/entries", headers=auth, json={"name": "b"}
        )).json()
        r = await client.post(
            f"/api/lists/{lid}/entries/reorder",
            headers=auth,
            json={"entry_ids": [b["id"], a["id"]]},
        )
        assert r.status_code == 204
        detail = await client.get(f"/api/lists/{lid}", headers=auth)
        names = [e["name"] for e in detail.json()["entries"]]
        assert names == ["b", "a"]

    async def test_reorder_partial_set_422(self, client, auth):
        lid = await self._make_list(client, auth)
        a = (await client.post(
            f"/api/lists/{lid}/entries", headers=auth, json={"name": "a"}
        )).json()
        await client.post(
            f"/api/lists/{lid}/entries", headers=auth, json={"name": "b"}
        )
        r = await client.post(
            f"/api/lists/{lid}/entries/reorder",
            headers=auth,
            json={"entry_ids": [a["id"]]},
        )
        assert r.status_code == 422

    async def test_cross_owner_entry_ops_404(self, client, auth, other_auth):
        c = await client.post("/api/lists", headers=other_auth, json={"kind": "generic", "title": "other"})
        lid = c.json()["id"]
        e = (await client.post(
            f"/api/lists/{lid}/entries", headers=other_auth, json={"name": "x"}
        )).json()
        r = await client.patch(
            f"/api/lists/{lid}/entries/{e['id']}", headers=auth, json={"name": "hijack"},
        )
        assert r.status_code == 404
