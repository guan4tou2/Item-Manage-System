from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from app.models.image import Image
from tests.test_locations_routes import _create, _owner_id
from tests.test_readonly_guard import _login, _member_auth
from tests.test_backup_import import _post


@pytest.fixture
async def auth_headers(client):
    return await _login(client, "floor_plan_user")


REGION = {"x": 0.1, "y": 0.2, "w": 0.3, "h": 0.4}


async def _image(client, headers, db_session):
    image = Image(
        owner_id=UUID(await _owner_id(client, headers)),
        filename="plan.png",
        mime_type="image/png",
        size_bytes=1,
        storage_path="plan.png",
    )
    db_session.add(image)
    await db_session.commit()
    return str(image.id)


async def _patch(client, headers, node, **body):
    return await client.patch(
        f"/api/locations/{node['id']}", headers=headers, json=body
    )


@pytest.mark.parametrize(
    "region",
    [
        {**REGION, "x": -0.1},
        {**REGION, "y": 1.1},
        {**REGION, "x": 0.8},
        {**REGION, "y": 0.8},
        {**REGION, "w": 0.01999},
        {**REGION, "h": 0},
        {**REGION, "x": "bad"},
        {**REGION, "x": "0.1"},
        {**REGION, "x": True},
        {**REGION, "extra": 1},
    ],
)
async def test_invalid_region(client, auth_headers, region):
    node = await _create(client, auth_headers)
    assert (
        await _patch(client, auth_headers, node, plan_region=region)
    ).status_code == 422


async def test_regions_consistency_and_views(client, auth_headers, db_session):
    floor = await _create(client, auth_headers)
    room = await _create(client, auth_headers, name="廚房", parent_id=floor["id"])
    for node in (floor, room):
        r = await _patch(client, auth_headers, node, plan_region=REGION)
        assert r.status_code == 422
        assert r.json()["detail"]["code"] == "parent_has_no_floor_plan"
    image = await _image(client, auth_headers, db_session)
    assert (
        await _patch(client, auth_headers, floor, floor_plan_image_id=image)
    ).status_code == 200
    edge = {"x": 0.98, "y": 0.98, "w": 0.02, "h": 0.02}
    assert (await _patch(client, auth_headers, room, plan_region=edge)).json()[
        "plan_region"
    ] == edge
    expected = {**REGION, "x": 0.1235}
    assert (
        await _patch(client, auth_headers, room, plan_region={**REGION, "x": 0.123456})
    ).json()["plan_region"] == expected
    assert (await _patch(client, auth_headers, room, name="房間")).json()[
        "plan_region"
    ] == expected

    async def current():
        rows = (await client.get("/api/locations", headers=auth_headers)).json()
        return next(row for row in rows if row["id"] == room["id"])["plan_region"]

    assert await current() == expected
    tree = (await client.get("/api/locations/tree", headers=auth_headers)).json()
    assert tree[0]["children"][0]["plan_region"] == expected
    replacement = await _image(client, auth_headers, db_session)
    await _patch(client, auth_headers, floor, floor_plan_image_id=replacement)
    assert await current() == expected
    await _patch(client, auth_headers, floor, floor_plan_image_id=None)
    assert await current() is None
    await _patch(client, auth_headers, floor, floor_plan_image_id=image)
    await _patch(client, auth_headers, room, plan_region=REGION)
    assert (await _patch(client, auth_headers, room, parent_id=None)).json()[
        "plan_region"
    ] is None
    await _patch(client, auth_headers, room, parent_id=floor["id"])
    await _patch(client, auth_headers, room, plan_region=REGION)
    assert (await _patch(client, auth_headers, room, plan_region=None)).json()[
        "plan_region"
    ] is None


async def test_image_ownership(client, auth_headers, db_session):
    floor = await _create(client, auth_headers)
    other = await _member_auth(client, "image_other", "editor")
    foreign = await _image(client, other, db_session)
    for image in (str(uuid4()), foreign):
        r = await _patch(client, auth_headers, floor, floor_plan_image_id=image)
        assert r.status_code == 422
        assert r.json()["detail"]["code"] == "invalid_floor_plan_image"
        r = await client.post(
            "/api/locations",
            headers=auth_headers,
            json={"name": "非法", "floor_plan_image_id": image},
        )
        assert r.status_code == 422


async def test_viewer_cannot_patch(client):
    viewer = await _member_auth(client, "plan_viewer", "viewer")
    r = await client.patch(
        "/api/locations/1", headers=viewer, json={"plan_region": REGION}
    )
    assert r.status_code == 403


async def test_backup_roundtrip_and_legacy(client, auth_headers, db_session):
    floor = await _create(client, auth_headers)
    room = await _create(client, auth_headers, name="廚房", parent_id=floor["id"])
    image = await _image(client, auth_headers, db_session)
    await _patch(client, auth_headers, floor, floor_plan_image_id=image)
    await _patch(client, auth_headers, room, plan_region=REGION)
    backup = (await client.get("/api/backup/export", headers=auth_headers)).json()
    other = await _member_auth(client, "plan_restore", "editor")
    r = await _post(client, other, doc=backup, dry_run=False)
    assert r.status_code == 200, r.text
    tree = (await client.get("/api/locations/tree", headers=other)).json()
    assert tree[0]["children"][0]["plan_region"] == REGION
    assert tree[0]["floor_plan_image_id"] is None
    legacy = {"format_version": 1, "locations": [{"id": 10, "name": "舊位置"}]}
    assert (await _post(client, other, doc=legacy, dry_run=False)).status_code == 200
    legacy["locations"][0].update(id=11, name="壞區域", plan_region={"x": -1})
    r = await _post(client, other, doc=legacy, dry_run=False)
    assert r.status_code == 200
    assert any("plan_region" in w for w in r.json()["warnings"])
    rows = (await client.get("/api/locations", headers=other)).json()
    assert next(row for row in rows if row["name"] == "壞區域")["plan_region"] is None


def test_rounding_preserves_bounds():
    from app.schemas.location import PlanRegion

    region = PlanRegion(x=0.00015, y=0.00015, w=0.99985, h=0.99985)
    assert region.x + region.w <= 1
    assert region.y + region.h <= 1
    assert PlanRegion.model_validate(region.model_dump()) == region
