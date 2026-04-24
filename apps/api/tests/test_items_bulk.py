from __future__ import annotations

import io

import pytest


@pytest.fixture
async def auth(client):
    await client.post(
        "/api/auth/register",
        json={"email": "bulk@t.io", "username": "bulk_user", "password": "secret1234"},
    )
    r = await client.post(
        "/api/auth/login",
        json={"username": "bulk_user", "password": "secret1234"},
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _csv(lines: list[str]) -> bytes:
    return ("\n".join(lines) + "\n").encode("utf-8")


# ---- export ------------------------------------------------------------


async def test_export_empty(client, auth):
    r = await client.get("/api/items/export.csv", headers=auth)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "filename=" in r.headers.get("content-disposition", "")
    body = r.text
    # header row only
    assert body.splitlines()[0].startswith("id,name,description,quantity,min_quantity")


async def test_export_includes_items_with_taxonomy(client, auth):
    cat = (await client.post("/api/categories", headers=auth, json={"name": "tools"})).json()
    loc = (
        await client.post(
            "/api/locations",
            headers=auth,
            json={"floor": "1F", "room": "garage"},
        )
    ).json()
    wh = (await client.post("/api/warehouses", headers=auth, json={"name": "Main"})).json()
    await client.post(
        "/api/items",
        headers=auth,
        json={
            "name": "hammer",
            "quantity": 2,
            "min_quantity": 1,
            "category_id": cat["id"],
            "location_id": loc["id"],
            "warehouse_id": wh["id"],
            "notes": "heavy",
        },
    )
    r = await client.get("/api/items/export.csv", headers=auth)
    lines = r.text.strip().splitlines()
    assert len(lines) == 2
    header = lines[0].split(",")
    row = lines[1].split(",")
    idx = {name: i for i, name in enumerate(header)}
    assert row[idx["name"]] == "hammer"
    assert row[idx["quantity"]] == "2"
    assert row[idx["min_quantity"]] == "1"
    assert row[idx["category_name"]] == "tools"
    assert row[idx["location_floor"]] == "1F"
    assert row[idx["location_room"]] == "garage"
    assert row[idx["warehouse_name"]] == "Main"
    assert row[idx["notes"]] == "heavy"


async def test_export_requires_auth(client):
    r = await client.get("/api/items/export.csv")
    assert r.status_code == 401


# ---- import: basic -----------------------------------------------------


async def test_import_minimum_columns(client, auth):
    csv_bytes = _csv(["name", "wrench", "screwdriver"])
    files = {"file": ("items.csv", csv_bytes, "text/csv")}
    r = await client.post("/api/items/bulk-import", headers=auth, files=files)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["created_count"] == 2
    assert body["total_rows"] == 2
    assert body["errors"] == []

    listed = (await client.get("/api/items", headers=auth)).json()
    names = {i["name"] for i in listed["items"]}
    assert {"wrench", "screwdriver"} <= names


async def test_import_auto_creates_taxonomy(client, auth):
    csv_bytes = _csv([
        "name,quantity,category_name,location_floor,location_room,warehouse_name",
        "drill,3,tools,2F,workshop,North",
        "saw,1,tools,2F,workshop,North",
    ])
    files = {"file": ("items.csv", csv_bytes, "text/csv")}
    r = await client.post("/api/items/bulk-import", headers=auth, files=files)
    assert r.status_code == 200
    assert r.json()["created_count"] == 2

    # only one category/location/warehouse should have been created (dedup)
    cats = (await client.get("/api/categories", headers=auth)).json()
    assert len([c for c in cats if c["name"] == "tools"]) == 1
    whs = (await client.get("/api/warehouses", headers=auth)).json()
    assert len([w for w in whs if w["name"] == "North"]) == 1
    locs = (await client.get("/api/locations", headers=auth)).json()
    assert len([l for l in locs if l["floor"] == "2F"]) == 1


async def test_import_reuses_existing_taxonomy(client, auth):
    # pre-create category with same name
    cat = (await client.post("/api/categories", headers=auth, json={"name": "tools"})).json()
    csv_bytes = _csv(["name,category_name", "drill,tools"])
    files = {"file": ("items.csv", csv_bytes, "text/csv")}
    r = await client.post("/api/items/bulk-import", headers=auth, files=files)
    assert r.status_code == 200
    assert r.json()["created_count"] == 1
    # no duplicate category
    cats = (await client.get("/api/categories", headers=auth)).json()
    assert len([c for c in cats if c["name"] == "tools"]) == 1
    assert cats[0]["id"] == cat["id"]


async def test_import_partial_success_reports_errors(client, auth):
    csv_bytes = _csv([
        "name,quantity",
        "good,2",
        ",5",           # missing name
        "bad_qty,abc",  # non-integer quantity
        "also_good,",   # empty quantity → defaults to 1
    ])
    files = {"file": ("items.csv", csv_bytes, "text/csv")}
    r = await client.post("/api/items/bulk-import", headers=auth, files=files)
    assert r.status_code == 200
    body = r.json()
    assert body["created_count"] == 2
    assert body["total_rows"] == 4
    assert len(body["errors"]) == 2
    row_nums = {e["row"] for e in body["errors"]}
    assert row_nums == {3, 4}


async def test_import_tolerates_utf8_bom(client, auth):
    csv_bytes = "\ufeff".encode("utf-8") + _csv(["name", "relic"])
    files = {"file": ("items.csv", csv_bytes, "text/csv")}
    r = await client.post("/api/items/bulk-import", headers=auth, files=files)
    assert r.status_code == 200
    assert r.json()["created_count"] == 1


# ---- import: edge cases ------------------------------------------------


async def test_import_missing_name_column(client, auth):
    csv_bytes = _csv(["description,quantity", "foo,1"])
    files = {"file": ("items.csv", csv_bytes, "text/csv")}
    r = await client.post("/api/items/bulk-import", headers=auth, files=files)
    assert r.status_code == 200
    body = r.json()
    assert body["created_count"] == 0
    assert body["errors"] and "name" in body["errors"][0]["reason"].lower()


async def test_import_empty_file(client, auth):
    files = {"file": ("items.csv", b"", "text/csv")}
    r = await client.post("/api/items/bulk-import", headers=auth, files=files)
    assert r.status_code == 400


async def test_import_rejects_bad_content_type(client, auth):
    files = {"file": ("items.zip", b"PK\x03\x04", "application/zip")}
    r = await client.post("/api/items/bulk-import", headers=auth, files=files)
    assert r.status_code == 415


async def test_import_requires_auth(client):
    files = {"file": ("items.csv", b"name\nfoo\n", "text/csv")}
    r = await client.post("/api/items/bulk-import", files=files)
    assert r.status_code == 401


# ---- ordering sanity: /items/export.csv must NOT match /items/{item_id} ---


async def test_export_url_does_not_hit_item_detail(client, auth):
    # If main.py registered routes in the wrong order, this would try to
    # parse "export.csv" as a UUID and 422 — this test locks the behavior.
    r = await client.get("/api/items/export.csv", headers=auth)
    assert r.status_code == 200
