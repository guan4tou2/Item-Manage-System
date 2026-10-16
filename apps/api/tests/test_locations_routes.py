from __future__ import annotations

import pytest
from sqlalchemy import select

from app.auth.password import hash_password
from app.models.item import Item
from app.models.location import Location
from app.models.user import User


@pytest.fixture
async def auth_headers(client):
    await client.post(
        "/api/auth/register",
        json={"email": "loc@t.io", "username": "loc_user", "password": "secret1234"},
    )
    r = await client.post(
        "/api/auth/login", json={"username": "loc_user", "password": "secret1234"}
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _create(client, headers, **payload) -> dict:
    defaults = {"name": "1F"}
    defaults.update(payload)
    r = await client.post("/api/locations", headers=headers, json=defaults)
    assert r.status_code == 201, r.text
    return r.json()


async def _owner_id(client, headers) -> str:
    return (await client.get("/api/users/me", headers=headers)).json()["id"]


async def _add_item(db_session, owner_id, name: str, location_id: int | None) -> Item:
    item = Item(owner_id=owner_id, name=name, location_id=location_id)
    db_session.add(item)
    await db_session.commit()
    return item


# ---------- 基本 CRUD ----------


async def test_list_empty(client, auth_headers):
    r = await client.get("/api/locations", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


async def test_create_root_and_child_with_paths(client, auth_headers):
    root = await _create(client, auth_headers, name="1F", kind="floor")
    assert root["parent_id"] is None
    assert root["path"] == "1F"
    assert root["sort_order"] == 0

    child = await _create(
        client, auth_headers, name="廚房", parent_id=root["id"], kind="room"
    )
    assert child["parent_id"] == root["id"]
    assert child["path"] == "1F / 廚房"

    grandchild = await _create(
        client, auth_headers, name="上櫃", parent_id=child["id"]
    )
    assert grandchild["path"] == "1F / 廚房 / 上櫃"
    assert grandchild["kind"] is None

    rows = (await client.get("/api/locations", headers=auth_headers)).json()
    assert [row["name"] for row in rows] == ["1F", "廚房", "上櫃"]


async def test_create_unknown_parent_404_and_duplicate_name_409(client, auth_headers):
    root = await _create(client, auth_headers, name="1F")

    missing = await client.post(
        "/api/locations",
        headers=auth_headers,
        json={"name": "廚房", "parent_id": 99999},
    )
    assert missing.status_code == 404

    await _create(client, auth_headers, name="廚房", parent_id=root["id"])
    duplicate = await client.post(
        "/api/locations",
        headers=auth_headers,
        json={"name": "廚房", "parent_id": root["id"]},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"]["code"] == "duplicate_name"


async def test_create_validation(client, auth_headers):
    empty = await client.post("/api/locations", headers=auth_headers, json={"name": ""})
    assert empty.status_code == 422

    long_kind = await client.post(
        "/api/locations",
        headers=auth_headers,
        json={"name": "1F", "kind": "k" * 21},
    )
    assert long_kind.status_code == 422

    extra = await client.post(
        "/api/locations", headers=auth_headers, json={"name": "1F", "floor": "1F"}
    )
    assert extra.status_code == 422


async def test_patch_rename_move_and_cycle(client, auth_headers):
    root = await _create(client, auth_headers, name="1F")
    kitchen = await _create(client, auth_headers, name="廚房", parent_id=root["id"])
    shelf = await _create(client, auth_headers, name="上櫃", parent_id=kitchen["id"])
    living = await _create(client, auth_headers, name="客廳", parent_id=root["id"])

    renamed = await client.patch(
        f"/api/locations/{shelf['id']}", headers=auth_headers, json={"name": "吊櫃"}
    )
    assert renamed.status_code == 200
    assert renamed.json()["path"] == "1F / 廚房 / 吊櫃"

    moved = await client.patch(
        f"/api/locations/{shelf['id']}",
        headers=auth_headers,
        json={"parent_id": living["id"]},
    )
    assert moved.json()["path"] == "1F / 客廳 / 吊櫃"

    to_root = await client.patch(
        f"/api/locations/{shelf['id']}", headers=auth_headers, json={"parent_id": None}
    )
    assert to_root.json()["path"] == "吊櫃"
    assert to_root.json()["parent_id"] is None

    cycle = await client.patch(
        f"/api/locations/{root['id']}",
        headers=auth_headers,
        json={"parent_id": kitchen["id"]},
    )
    assert cycle.status_code == 422
    assert cycle.json()["detail"]["code"] == "cycle"

    unknown = await client.patch(
        "/api/locations/99999", headers=auth_headers, json={"name": "X"}
    )
    assert unknown.status_code == 404


async def test_delete_limits_and_success(client, auth_headers, db_session):
    root = await _create(client, auth_headers, name="1F")
    kitchen = await _create(client, auth_headers, name="廚房", parent_id=root["id"])
    shelf = await _create(client, auth_headers, name="上櫃", parent_id=kitchen["id"])

    with_children = await client.delete(
        f"/api/locations/{kitchen['id']}", headers=auth_headers
    )
    assert with_children.status_code == 409
    assert with_children.json()["detail"] == {
        "code": "has_children",
        "items": 0,
        "children": 1,
    }

    owner_id = await _owner_id(client, auth_headers)
    await _add_item(db_session, owner_id, "牛奶", shelf["id"])
    with_items = await client.delete(
        f"/api/locations/{shelf['id']}", headers=auth_headers
    )
    assert with_items.status_code == 409
    assert with_items.json()["detail"] == {
        "code": "has_items",
        "items": 1,
        "children": 0,
    }

    ok = await client.delete(
        f"/api/locations/{(await _create(client, auth_headers, name='儲藏室'))['id']}",
        headers=auth_headers,
    )
    assert ok.status_code == 204
    assert (
        await client.delete("/api/locations/99999", headers=auth_headers)
    ).status_code == 404


# ---------- 樹與路徑 ----------


async def test_tree_endpoint_nested_with_item_counts(client, auth_headers, db_session):
    root = await _create(client, auth_headers, name="1F", kind="floor")
    kitchen = await _create(client, auth_headers, name="廚房", parent_id=root["id"])
    shelf = await _create(client, auth_headers, name="上櫃", parent_id=kitchen["id"])
    owner_id = await _owner_id(client, auth_headers)
    await _add_item(db_session, owner_id, "牛奶", shelf["id"])
    await _add_item(db_session, owner_id, "雞蛋", shelf["id"])

    tree = (await client.get("/api/locations/tree", headers=auth_headers)).json()

    assert [node["name"] for node in tree] == ["1F"]
    floor = tree[0]
    assert floor["item_count"] == 0
    assert floor["path"] == "1F"
    room = floor["children"][0]
    assert room["name"] == "廚房" and room["path"] == "1F / 廚房"
    cupboard = room["children"][0]
    assert cupboard["name"] == "上櫃" and cupboard["item_count"] == 2
    assert cupboard["children"] == []


async def test_path_endpoint(client, auth_headers):
    root = await _create(client, auth_headers, name="1F", kind="floor")
    kitchen = await _create(client, auth_headers, name="廚房", parent_id=root["id"])
    shelf = await _create(client, auth_headers, name="上櫃", parent_id=kitchen["id"])

    payload = (
        await client.get(f"/api/locations/{shelf['id']}/path", headers=auth_headers)
    ).json()

    assert payload["path"] == "1F / 廚房 / 上櫃"
    assert [node["name"] for node in payload["nodes"]] == ["1F", "廚房", "上櫃"]
    assert payload["nodes"][0]["kind"] == "floor"

    missing = await client.get("/api/locations/99999/path", headers=auth_headers)
    assert missing.status_code == 404


# ---------- 權限與隔離 ----------


async def test_endpoints_require_auth(client):
    assert (await client.get("/api/locations")).status_code == 401
    assert (await client.get("/api/locations/tree")).status_code == 401
    assert (await client.get("/api/locations/1/path")).status_code == 401
    assert (await client.post("/api/locations", json={"name": "1F"})).status_code == 401
    assert (
        await client.post("/api/locations/reorder", json={"location_ids": [1]})
    ).status_code == 401
    assert (await client.patch("/api/locations/1", json={"name": "x"})).status_code == 401
    assert (await client.delete("/api/locations/1")).status_code == 401


async def test_owner_isolation(client, auth_headers, db_session):
    mine = await _create(client, auth_headers, name="我的樓層")

    await client.post(
        "/api/auth/register",
        json={"email": "loc2@t.io", "username": "loc_user_2", "password": "secret1234"},
    )
    other_login = await client.post(
        "/api/auth/login", json={"username": "loc_user_2", "password": "secret1234"}
    )
    other = {"Authorization": f"Bearer {other_login.json()['access_token']}"}

    assert (await client.get("/api/locations", headers=other)).json() == []
    assert (await client.get("/api/locations/tree", headers=other)).json() == []
    assert (
        await client.get(f"/api/locations/{mine['id']}/path", headers=other)
    ).status_code == 404
    assert (
        await client.patch(
            f"/api/locations/{mine['id']}", headers=other, json={"name": "搶走"}
        )
    ).status_code == 404
    assert (
        await client.delete(f"/api/locations/{mine['id']}", headers=other)
    ).status_code == 404

    # 樹上仍保留原節點
    remaining = (
        await db_session.execute(select(Location).where(Location.id == mine["id"]))
    ).scalar_one_or_none()
    assert remaining is not None
