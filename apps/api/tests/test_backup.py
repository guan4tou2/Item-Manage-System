from __future__ import annotations
import pytest


@pytest.fixture
async def auth(client):
    await client.post("/api/auth/register", json={"email": "b@t.io", "username": "b_user", "password": "secret1234"})
    r = await client.post("/api/auth/login", json={"username": "b_user", "password": "secret1234"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def test_export_empty(client, auth):
    r = await client.get("/api/backup/export", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["format_version"] == 3
    assert body["items"] == []
    assert body["categories"] == []
    assert "Content-Disposition" in r.headers
    assert "attachment" in r.headers["Content-Disposition"]


async def test_export_includes_items(client, auth):
    await client.post("/api/items", headers=auth, json={"name": "A", "quantity": 3, "tag_names": ["x"]})
    body = (await client.get("/api/backup/export", headers=auth)).json()
    assert len(body["items"]) == 1
    assert body["items"][0]["name"] == "A"
    assert body["items"][0]["tag_names"] == ["x"]


async def test_export_includes_lists(client, auth):
    lst = (await client.post("/api/lists", headers=auth, json={"kind": "generic", "title": "test"})).json()
    await client.post(f"/api/lists/{lst['id']}/entries", headers=auth, json={"name": "a"})
    body = (await client.get("/api/backup/export", headers=auth)).json()
    assert len(body["lists"]) == 1
    assert len(body["lists"][0]["entries"]) == 1


async def test_export_includes_warehouses(client, auth):
    await client.post("/api/warehouses", headers=auth, json={"name": "家裡"})
    body = (await client.get("/api/backup/export", headers=auth)).json()
    assert len(body["warehouses"]) == 1

async def test_export_includes_tree_locations(client, auth):
    floor = (
        await client.post(
            "/api/locations", headers=auth, json={"name": "1F", "kind": "floor"}
        )
    ).json()
    room = (
        await client.post(
            "/api/locations",
            headers=auth,
            json={"name": "廚房", "parent_id": floor["id"], "kind": "room"},
        )
    ).json()

    body = (await client.get("/api/backup/export", headers=auth)).json()

    assert body["format_version"] == 3
    by_id = {loc["id"]: loc for loc in body["locations"]}
    assert by_id[floor["id"]]["parent_id"] is None
    assert by_id[room["id"]]["parent_id"] == floor["id"]
    assert by_id[room["id"]]["name"] == "廚房"
    assert by_id[room["id"]]["kind"] == "room"
    assert "sort_order" in by_id[room["id"]]
    # 舊三欄不再輸出
    assert "floor" not in by_id[room["id"]]


async def test_export_items_include_cost(client, auth):
    await client.post("/api/items", headers=auth, json={"name": "有價", "cost": "12.30"})
    await client.post("/api/items", headers=auth, json={"name": "無價"})
    body = (await client.get("/api/backup/export", headers=auth)).json()
    by_name = {i["name"]: i for i in body["items"]}
    assert by_name["有價"]["cost"] == "12.30"
    assert by_name["無價"]["cost"] is None


async def test_export_with_priced_list_does_not_crash(client, auth):
    lst = (
        await client.post(
            "/api/lists", headers=auth, json={"kind": "generic", "title": "t", "budget": "500.00"}
        )
    ).json()
    await client.post(
        f"/api/lists/{lst['id']}/entries",
        headers=auth,
        json={"name": "a", "price": "99.50"},
    )
    r = await client.get("/api/backup/export", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["lists"][0]["budget"] == "500.00"
    assert body["lists"][0]["entries"][0]["price"] == "99.50"
