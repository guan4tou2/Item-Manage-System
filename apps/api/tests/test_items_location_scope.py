from __future__ import annotations

import pytest


@pytest.fixture
async def auth(client):
    await client.post(
        "/api/auth/register",
        json={"email": "scope@t.io", "username": "scope_user", "password": "secret1234"},
    )
    r = await client.post(
        "/api/auth/login", json={"username": "scope_user", "password": "secret1234"}
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _location(client, auth, **payload) -> dict:
    r = await client.post("/api/locations", headers=auth, json=payload)
    assert r.status_code == 201, r.text
    return r.json()


async def _item(client, auth, name: str, location_id: int | None = None) -> dict:
    payload: dict = {"name": name}
    if location_id is not None:
        payload["location_id"] = location_id
    r = await client.post("/api/items", headers=auth, json=payload)
    assert r.status_code == 201, r.text
    return r.json()


async def _tree(client, auth) -> dict[str, dict]:
    floor = await _location(client, auth, name="1F", kind="floor")
    kitchen = await _location(
        client, auth, name="廚房", parent_id=floor["id"], kind="room"
    )
    shelf = await _location(client, auth, name="上櫃", parent_id=kitchen["id"])
    return {"1F": floor, "廚房": kitchen, "上櫃": shelf}


async def test_location_filter_defaults_to_subtree(client, auth):
    nodes = await _tree(client, auth)
    await _item(client, auth, "在樓層", nodes["1F"]["id"])
    await _item(client, auth, "在櫃子", nodes["上櫃"]["id"])
    await _item(client, auth, "未指派")

    subtree = (
        await client.get(
            f"/api/items?location_id={nodes['1F']['id']}", headers=auth
        )
    ).json()
    assert {i["name"] for i in subtree["items"]} == {"在樓層", "在櫃子"}
    assert subtree["total"] == 2

    exact = (
        await client.get(
            f"/api/items?location_id={nodes['1F']['id']}&location_scope=exact",
            headers=auth,
        )
    ).json()
    assert {i["name"] for i in exact["items"]} == {"在樓層"}

    leaf = (
        await client.get(
            f"/api/items?location_id={nodes['上櫃']['id']}", headers=auth
        )
    ).json()
    assert {i["name"] for i in leaf["items"]} == {"在櫃子"}


async def test_location_filter_combines_with_other_filters(client, auth):
    nodes = await _tree(client, auth)
    await client.post(
        "/api/items",
        headers=auth,
        json={"name": "牛奶", "location_id": nodes["上櫃"]["id"], "tag_names": ["飲料"]},
    )
    await client.post(
        "/api/items", headers=auth, json={"name": "水餃", "location_id": nodes["上櫃"]["id"]}
    )

    r = await client.get(
        f"/api/items?location_id={nodes['廚房']['id']}&q=牛奶", headers=auth
    )
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "牛奶"


async def test_item_read_exposes_full_location_path(client, auth):
    nodes = await _tree(client, auth)
    item = await _item(client, auth, "牛奶", nodes["上櫃"]["id"])

    detail = (await client.get(f"/api/items/{item['id']}", headers=auth)).json()
    assert detail["location"]["path"] == "1F / 廚房 / 上櫃"
    assert detail["location"]["name"] == "上櫃"
    assert detail["location"]["kind"] is None
    assert detail["location"]["parent_id"] == nodes["廚房"]["id"]

    listed = (await client.get("/api/items", headers=auth)).json()
    assert listed["items"][0]["location"]["path"] == "1F / 廚房 / 上櫃"


async def test_item_without_location_has_null_location(client, auth):
    item = await _item(client, auth, "未指派")
    detail = (await client.get(f"/api/items/{item['id']}", headers=auth)).json()
    assert detail["location"] is None


async def test_path_updates_after_move_are_reflected(client, auth):
    nodes = await _tree(client, auth)
    item = await _item(client, auth, "牛奶", nodes["上櫃"]["id"])

    await client.patch(
        f"/api/locations/{nodes['上櫃']['id']}",
        headers=auth,
        json={"parent_id": nodes["1F"]["id"]},
    )

    detail = (await client.get(f"/api/items/{item['id']}", headers=auth)).json()
    assert detail["location"]["path"] == "1F / 上櫃"


async def test_unknown_location_filter_returns_empty(client, auth):
    await _tree(client, auth)
    await _item(client, auth, "牛奶")

    subtree = (await client.get("/api/items?location_id=99999", headers=auth)).json()
    assert subtree["total"] == 0
    exact = (
        await client.get("/api/items?location_id=99999&location_scope=exact", headers=auth)
    ).json()
    assert exact["total"] == 0


async def test_invalid_scope_is_422(client, auth):
    r = await client.get("/api/items?location_id=1&location_scope=bogus", headers=auth)
    assert r.status_code == 422


async def test_creating_item_with_unknown_location_is_422(client, auth):
    r = await client.post(
        "/api/items", headers=auth, json={"name": "x", "location_id": 99999}
    )
    assert r.status_code == 422


async def test_bulk_move_items_between_nodes(client, auth):
    nodes = await _tree(client, auth)
    first = await _item(client, auth, "牛奶", nodes["上櫃"]["id"])
    second = await _item(client, auth, "水餃", nodes["上櫃"]["id"])

    r = await client.patch(
        "/api/items/bulk",
        headers=auth,
        json={
            "item_ids": [first["id"], second["id"]],
            "location_id": nodes["1F"]["id"],
        },
    )
    assert r.status_code == 200

    moved = (await client.get(f"/api/items/{first['id']}", headers=auth)).json()
    assert moved["location"]["path"] == "1F"

    # 原節點已無物品 → 可刪除（刪除限制的實際流程）
    assert (
        await client.delete(f"/api/locations/{nodes['上櫃']['id']}", headers=auth)
    ).status_code == 204
