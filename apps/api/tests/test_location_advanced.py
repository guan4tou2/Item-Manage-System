from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models.location import Location


@pytest.fixture
async def auth(client):
    await client.post(
        "/api/auth/register",
        json={"email": "locadv@t.io", "username": "loc_adv", "password": "secret1234"},
    )
    r = await client.post(
        "/api/auth/login", json={"username": "loc_adv", "password": "secret1234"}
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _create(client, auth, **payload) -> dict:
    r = await client.post("/api/locations", headers=auth, json=payload)
    assert r.status_code == 201, r.text
    return r.json()


async def test_create_with_sort_order(client, auth):
    node = await _create(client, auth, name="1F", sort_order=5)
    assert node["sort_order"] == 5


async def test_default_sort_order_is_zero(client, auth):
    node = await _create(client, auth, name="1F")
    assert node["sort_order"] == 0


async def test_list_orders_by_sort_order_then_name(client, auth):
    root = await _create(client, auth, name="1F")
    await _create(client, auth, name="C", parent_id=root["id"], sort_order=2)
    await _create(client, auth, name="A", parent_id=root["id"], sort_order=1)
    await _create(client, auth, name="B", parent_id=root["id"], sort_order=1)

    rows = (await client.get("/api/locations", headers=auth)).json()

    assert [row["name"] for row in rows] == ["1F", "A", "B", "C"]


async def test_patch_floor_plan_image_id(client, auth):
    node = await _create(client, auth, name="1F")
    image_id = "11111111-1111-4111-8111-111111111111"

    r = await client.patch(
        f"/api/locations/{node['id']}",
        headers=auth,
        json={"floor_plan_image_id": image_id},
    )
    assert r.status_code == 200
    assert r.json()["floor_plan_image_id"] == image_id


async def test_patch_sort_order(client, auth):
    node = await _create(client, auth, name="1F", sort_order=0)
    r = await client.patch(
        f"/api/locations/{node['id']}", headers=auth, json={"sort_order": 3}
    )
    assert r.json()["sort_order"] == 3


async def test_patch_kind_accepts_free_text_and_presets(client, auth):
    node = await _create(client, auth, name="1F")
    preset = await client.patch(
        f"/api/locations/{node['id']}", headers=auth, json={"kind": "shelf"}
    )
    assert preset.json()["kind"] == "shelf"
    free = await client.patch(
        f"/api/locations/{node['id']}", headers=auth, json={"kind": "車庫層板"}
    )
    assert free.json()["kind"] == "車庫層板"


async def test_reorder_rewrites_positions(client, auth):
    root = await _create(client, auth, name="1F")
    a = await _create(client, auth, name="A", parent_id=root["id"], sort_order=0)
    b = await _create(client, auth, name="B", parent_id=root["id"], sort_order=1)
    c = await _create(client, auth, name="C", parent_id=root["id"], sort_order=2)

    r = await client.post(
        "/api/locations/reorder",
        headers=auth,
        json={"parent_id": root["id"], "location_ids": [c["id"], a["id"], b["id"]]},
    )
    assert r.status_code == 200
    names = [row["name"] for row in r.json()]
    assert names == ["1F", "C", "A", "B"]

    roots = await client.post(
        "/api/locations/reorder",
        headers=auth,
        json={"parent_id": None, "location_ids": [root["id"]]},
    )
    assert roots.status_code == 200


async def test_reorder_rejects_duplicates_unknown_and_incomplete(client, auth):
    root = await _create(client, auth, name="1F")
    a = await _create(client, auth, name="A", parent_id=root["id"])
    await _create(client, auth, name="B", parent_id=root["id"])

    duplicates = await client.post(
        "/api/locations/reorder",
        headers=auth,
        json={"parent_id": root["id"], "location_ids": [a["id"], a["id"]]},
    )
    assert duplicates.status_code == 422

    unknown_parent = await client.post(
        "/api/locations/reorder",
        headers=auth,
        json={"parent_id": 99999, "location_ids": [a["id"]]},
    )
    assert unknown_parent.status_code == 404

    incomplete = await client.post(
        "/api/locations/reorder",
        headers=auth,
        json={"parent_id": root["id"], "location_ids": [a["id"]]},
    )
    assert incomplete.status_code == 422
    assert incomplete.json()["detail"]["code"] == "invalid_siblings"


async def test_reorder_rejects_cross_owner(client, auth):
    root = await _create(client, auth, name="1F")
    child = await _create(client, auth, name="廚房", parent_id=root["id"])

    await client.post(
        "/api/auth/register",
        json={"email": "locadv2@t.io", "username": "loc_adv_2", "password": "secret1234"},
    )
    login = await client.post(
        "/api/auth/login", json={"username": "loc_adv_2", "password": "secret1234"}
    )
    other = {"Authorization": f"Bearer {login.json()['access_token']}"}
    mine = await _create(client, other, name="別人的")

    r = await client.post(
        "/api/locations/reorder",
        headers=other,
        json={"parent_id": None, "location_ids": [mine["id"], child["id"]]},
    )
    assert r.status_code == 422


async def test_reorder_requires_auth(client):
    r = await client.post("/api/locations/reorder", json={"location_ids": [1]})
    assert r.status_code == 401


async def test_delete_cascades_nothing_and_keeps_tree_consistent(client, auth, db_session):
    root = await _create(client, auth, name="1F")
    child = await _create(client, auth, name="廚房", parent_id=root["id"])

    assert (
        await client.delete(f"/api/locations/{child['id']}", headers=auth)
    ).status_code == 204

    rows = (await db_session.execute(select(Location))).scalars().all()
    assert [row.name for row in rows] == ["1F"]

    tree = (await client.get("/api/locations/tree", headers=auth)).json()
    assert tree[0]["children"] == []
