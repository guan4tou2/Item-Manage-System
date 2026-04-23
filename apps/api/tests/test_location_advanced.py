from __future__ import annotations

import io
import struct
import zlib

import pytest


def _tiny_png() -> bytes:
    signature = b"\x89PNG\r\n\x1a\n"

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    raw = b"\x00\xff\x00\x00"
    idat = zlib.compress(raw)
    return signature + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


@pytest.fixture(autouse=True)
def _isolated_media(tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path))
    from app.config import get_settings
    get_settings.cache_clear()


@pytest.fixture
async def auth(client):
    await client.post(
        "/api/auth/register",
        json={"email": "loc_adv@t.io", "username": "loc_adv_user", "password": "secret1234"},
    )
    r = await client.post(
        "/api/auth/login",
        json={"username": "loc_adv_user", "password": "secret1234"},
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _create(client, auth, floor: str, sort_order: int | None = None) -> dict:
    payload: dict = {"floor": floor}
    if sort_order is not None:
        payload["sort_order"] = sort_order
    r = await client.post("/api/locations", headers=auth, json=payload)
    assert r.status_code == 201, r.text
    return r.json()


async def test_create_with_sort_order(client, auth):
    body = await _create(client, auth, "3F", sort_order=5)
    assert body["sort_order"] == 5


async def test_list_orders_by_sort_order(client, auth):
    # create in non-natural floor order to verify sort_order wins over alphabetical
    a = await _create(client, auth, "3F", sort_order=2)
    b = await _create(client, auth, "1F", sort_order=0)
    c = await _create(client, auth, "2F", sort_order=1)
    r = await client.get("/api/locations", headers=auth)
    assert r.status_code == 200
    ids = [row["id"] for row in r.json()]
    assert ids == [b["id"], c["id"], a["id"]]


async def test_patch_floor_plan_image_id(client, auth):
    # upload an image first
    png = _tiny_png()
    files = {"file": ("fp.png", png, "image/png")}
    img = (await client.post("/api/images", headers=auth, files=files)).json()
    loc = await _create(client, auth, "1F")
    r = await client.patch(
        f"/api/locations/{loc['id']}",
        headers=auth,
        json={"floor_plan_image_id": img["id"]},
    )
    assert r.status_code == 200
    assert r.json()["floor_plan_image_id"] == img["id"]


async def test_patch_sort_order(client, auth):
    loc = await _create(client, auth, "1F", sort_order=0)
    r = await client.patch(
        f"/api/locations/{loc['id']}",
        headers=auth,
        json={"sort_order": 99},
    )
    assert r.status_code == 200
    assert r.json()["sort_order"] == 99


async def test_reorder_rewrites_positions(client, auth):
    a = await _create(client, auth, "A-floor", sort_order=0)
    b = await _create(client, auth, "B-floor", sort_order=1)
    c = await _create(client, auth, "C-floor", sort_order=2)

    # reverse order
    r = await client.post(
        "/api/locations/reorder",
        headers=auth,
        json={"location_ids": [c["id"], b["id"], a["id"]]},
    )
    assert r.status_code == 200, r.text
    rows = r.json()
    ids = [row["id"] for row in rows]
    assert ids == [c["id"], b["id"], a["id"]]
    sort_orders = {row["id"]: row["sort_order"] for row in rows}
    assert sort_orders[c["id"]] == 0
    assert sort_orders[b["id"]] == 1
    assert sort_orders[a["id"]] == 2


async def test_reorder_rejects_duplicates(client, auth):
    a = await _create(client, auth, "A", sort_order=0)
    r = await client.post(
        "/api/locations/reorder",
        headers=auth,
        json={"location_ids": [a["id"], a["id"]]},
    )
    assert r.status_code == 400


async def test_reorder_rejects_unknown_id(client, auth):
    a = await _create(client, auth, "A", sort_order=0)
    r = await client.post(
        "/api/locations/reorder",
        headers=auth,
        json={"location_ids": [a["id"], 999999]},
    )
    assert r.status_code == 404


async def test_reorder_rejects_cross_owner(client, auth):
    # owner 1 creates a location
    owned = await _create(client, auth, "A", sort_order=0)
    # register a second user
    await client.post(
        "/api/auth/register",
        json={"email": "other_loc@t.io", "username": "other_loc_user", "password": "secret1234"},
    )
    r = await client.post(
        "/api/auth/login",
        json={"username": "other_loc_user", "password": "secret1234"},
    )
    other = {"Authorization": f"Bearer {r.json()['access_token']}"}
    # other user attempts to reorder owner1's location id
    resp = await client.post(
        "/api/locations/reorder",
        headers=other,
        json={"location_ids": [owned["id"]]},
    )
    assert resp.status_code == 404


async def test_reorder_requires_auth(client):
    r = await client.post("/api/locations/reorder", json={"location_ids": [1]})
    assert r.status_code == 401


async def test_default_sort_order_is_zero(client, auth):
    body = await _create(client, auth, "1F")
    assert body["sort_order"] == 0
