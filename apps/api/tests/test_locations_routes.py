import pytest


@pytest.fixture
async def auth_headers(client):
    await client.post("/api/auth/register", json={
        "email": "loc@t.io", "username": "loc_user", "password": "secret1234",
    })
    resp = await client.post("/api/auth/login", json={
        "username": "loc_user", "password": "secret1234",
    })
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


class TestLocations:
    async def test_list_empty(self, client, auth_headers):
        resp = await client.get("/api/locations", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_create_minimal(self, client, auth_headers):
        resp = await client.post("/api/locations", headers=auth_headers,
                                 json={"floor": "1F"})
        assert resp.status_code == 201
        body = resp.json()
        assert body["floor"] == "1F"
        assert body["room"] is None
        assert body["zone"] is None

    async def test_create_full(self, client, auth_headers):
        resp = await client.post("/api/locations", headers=auth_headers,
                                 json={"floor": "1F", "room": "kitchen", "zone": "pantry"})
        assert resp.status_code == 201

    async def test_update(self, client, auth_headers):
        created = await client.post("/api/locations", headers=auth_headers, json={"floor": "1F"})
        lid = created.json()["id"]
        resp = await client.patch(f"/api/locations/{lid}", headers=auth_headers, json={"room": "den"})
        assert resp.status_code == 200
        assert resp.json()["room"] == "den"

    async def test_delete(self, client, auth_headers):
        created = await client.post("/api/locations", headers=auth_headers, json={"floor": "1F"})
        lid = created.json()["id"]
        resp = await client.delete(f"/api/locations/{lid}", headers=auth_headers)
        assert resp.status_code == 204
        resp2 = await client.patch(f"/api/locations/{lid}", headers=auth_headers, json={"room": "x"})
        assert resp2.status_code == 404

    async def test_validation_empty_floor(self, client, auth_headers):
        resp = await client.post("/api/locations", headers=auth_headers, json={"floor": ""})
        assert resp.status_code == 422

    async def test_unauthenticated_401(self, client):
        assert (await client.get("/api/locations")).status_code == 401
