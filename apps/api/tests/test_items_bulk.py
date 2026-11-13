from __future__ import annotations


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
    assert body.splitlines()[0].startswith(
        "id,name,description,barcode,quantity,min_quantity"
    )


async def test_export_includes_items_with_taxonomy(client, auth):
    cat = (await client.post("/api/categories", headers=auth, json={"name": "tools"})).json()
    floor = (
        await client.post(
            "/api/locations", headers=auth, json={"name": "1F", "kind": "floor"}
        )
    ).json()
    loc = (
        await client.post(
            "/api/locations",
            headers=auth,
            json={"name": "garage", "parent_id": floor["id"], "kind": "room"},
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
    assert row[idx["location_path"]] == "1F / garage"
    assert row[idx["warehouse_name"]] == "Main"
    assert row[idx["notes"]] == "heavy"


async def test_export_requires_auth(client):
    r = await client.get("/api/items/export.csv")
    assert r.status_code == 401


async def test_export_includes_barcode(client, auth):
    await client.post(
        "/api/items", headers=auth, json={"name": "牛奶", "barcode": "4710085200016"}
    )
    r = await client.get("/api/items/export.csv", headers=auth)
    lines = r.text.strip().splitlines()
    header = lines[0].split(",")
    row = lines[1].split(",")
    idx = {name: i for i, name in enumerate(header)}
    assert row[idx["barcode"]] == "4710085200016"


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


async def test_import_barcode_canonicalizes_and_roundtrips(client, auth):
    csv_bytes = _csv(["name,barcode", "牛奶,471-0085-200016"])
    files = {"file": ("items.csv", csv_bytes, "text/csv")}
    r = await client.post("/api/items/bulk-import", headers=auth, files=files)
    assert r.status_code == 200
    assert r.json()["created_count"] == 1

    listed = (await client.get("/api/items", headers=auth)).json()
    assert listed["items"][0]["barcode"] == "4710085200016"

    # round-trip：匯出再匯入不丟 barcode
    exported = (await client.get("/api/items/export.csv", headers=auth)).text
    files2 = {"file": ("items.csv", exported.encode("utf-8"), "text/csv")}
    r2 = await client.post("/api/items/bulk-import", headers=auth, files=files2)
    assert r2.json()["created_count"] == 1
    listed2 = (await client.get("/api/items", headers=auth)).json()
    assert sorted(i["barcode"] for i in listed2["items"]) == [
        "4710085200016",
        "4710085200016",
    ]


async def test_import_auto_creates_taxonomy(client, auth):
    csv_bytes = _csv([
        "name,quantity,category_name,location_path,warehouse_name",
        "drill,3,tools,2F / workshop,North",
        "saw,1,tools,2F / workshop,North",
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
    paths = {l["path"] for l in locs}
    assert "2F" in paths and "2F / workshop" in paths


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


# ---- Phase 19: tag round-trip ------------------------------------------


def _tag_names_of(item: dict) -> set[str]:
    return {t["name"] for t in item.get("tags", [])}


def _tag_ids_of(item: dict) -> list[int]:
    return [t["id"] for t in item.get("tags", [])]


async def test_export_includes_pipe_delimited_tags(client, auth):
    item = (
        await client.post(
            "/api/items", headers=auth, json={"name": "blade", "tag_names": ["sharp", "kitchen"]}
        )
    ).json()
    assert len(item.get("tags", [])) == 2

    r = await client.get("/api/items/export.csv", headers=auth)
    lines = r.text.strip().splitlines()
    header = lines[0].split(",")
    idx = header.index("tag_names")
    blade_row = next(line for line in lines[1:] if line.split(",")[1] == "blade")
    parts = blade_row.split(",")
    # sorted alphabetically by the export code
    assert parts[idx] == "kitchen|sharp"


async def test_export_empty_tags_emits_blank_cell(client, auth):
    await client.post("/api/items", headers=auth, json={"name": "plain"})
    r = await client.get("/api/items/export.csv", headers=auth)
    lines = r.text.strip().splitlines()
    header = lines[0].split(",")
    idx = header.index("tag_names")
    data_row = lines[1].split(",")
    assert data_row[idx] == ""


async def test_import_creates_tags_from_pipe_delimited_cell(client, auth):
    csv_bytes = _csv([
        "name,tag_names",
        "wok,kitchen|heavy",
        "pan,kitchen|light",
    ])
    files = {"file": ("items.csv", csv_bytes, "text/csv")}
    r = await client.post("/api/items/bulk-import", headers=auth, files=files)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["created_count"] == 2
    assert body["errors"] == []

    listed = (await client.get("/api/items", headers=auth)).json()
    by_name = {i["name"]: i for i in listed["items"]}
    assert _tag_names_of(by_name["wok"]) == {"kitchen", "heavy"}
    assert _tag_names_of(by_name["pan"]) == {"kitchen", "light"}


async def test_import_reuses_existing_tag(client, auth):
    seed = (
        await client.post(
            "/api/items", headers=auth, json={"name": "seed", "tag_names": ["kitchen"]}
        )
    ).json()
    seed_ids = _tag_ids_of(seed)
    assert len(seed_ids) == 1
    kitchen_id = seed_ids[0]

    csv_bytes = _csv(["name,tag_names", "wok,kitchen"])
    files = {"file": ("items.csv", csv_bytes, "text/csv")}
    r = await client.post("/api/items/bulk-import", headers=auth, files=files)
    assert r.status_code == 200, r.text

    listed = (await client.get("/api/items", headers=auth)).json()
    wok = next(i for i in listed["items"] if i["name"] == "wok")
    assert _tag_ids_of(wok) == [kitchen_id]


async def test_import_dedupes_within_one_cell(client, auth):
    csv_bytes = _csv(["name,tag_names", "wok,kitchen|kitchen| |kitchen "])
    files = {"file": ("items.csv", csv_bytes, "text/csv")}
    r = await client.post("/api/items/bulk-import", headers=auth, files=files)
    assert r.status_code == 200, r.text

    listed = (await client.get("/api/items", headers=auth)).json()
    wok = next(i for i in listed["items"] if i["name"] == "wok")
    assert _tag_names_of(wok) == {"kitchen"}


async def test_import_empty_tag_cell_attaches_no_tags(client, auth):
    csv_bytes = _csv(["name,tag_names", "wok,"])
    files = {"file": ("items.csv", csv_bytes, "text/csv")}
    r = await client.post("/api/items/bulk-import", headers=auth, files=files)
    assert r.status_code == 200, r.text
    listed = (await client.get("/api/items", headers=auth)).json()
    wok = next(i for i in listed["items"] if i["name"] == "wok")
    assert _tag_names_of(wok) == set()


async def test_import_does_not_leak_tags_across_owners(client, auth):
    csv_bytes = _csv(["name,tag_names", "wok,kitchen"])
    files = {"file": ("items.csv", csv_bytes, "text/csv")}
    r = await client.post("/api/items/bulk-import", headers=auth, files=files)
    assert r.status_code == 200

    await client.post(
        "/api/auth/register",
        json={"email": "other@t.io", "username": "other_bulk", "password": "secret1234"},
    )
    r2 = await client.post(
        "/api/auth/login", json={"username": "other_bulk", "password": "secret1234"}
    )
    other = {"Authorization": f"Bearer {r2.json()['access_token']}"}

    files = {"file": ("items.csv", csv_bytes, "text/csv")}
    r3 = await client.post("/api/items/bulk-import", headers=other, files=files)
    assert r3.status_code == 200

    b_listed = (await client.get("/api/items", headers=other)).json()
    b_wok = next(i for i in b_listed["items"] if i["name"] == "wok")
    b_ids = _tag_ids_of(b_wok)
    assert len(b_ids) == 1

    a_listed = (await client.get("/api/items", headers=auth)).json()
    a_wok = next(i for i in a_listed["items"] if i["name"] == "wok")
    a_ids = _tag_ids_of(a_wok)
    assert a_ids[0] != b_ids[0]


async def test_import_roundtrip_preserves_tags(client, auth):
    await client.post(
        "/api/items", headers=auth, json={"name": "blade", "tag_names": ["sharp"]}
    )
    await client.post(
        "/api/items", headers=auth, json={"name": "wok", "tag_names": ["kitchen", "heavy"]}
    )

    exported = (await client.get("/api/items/export.csv", headers=auth)).text

    await client.post(
        "/api/auth/register",
        json={"email": "rt@t.io", "username": "rt_user", "password": "secret1234"},
    )
    r = await client.post(
        "/api/auth/login", json={"username": "rt_user", "password": "secret1234"}
    )
    rt = {"Authorization": f"Bearer {r.json()['access_token']}"}

    files = {"file": ("items.csv", exported.encode("utf-8"), "text/csv")}
    resp = await client.post("/api/items/bulk-import", headers=rt, files=files)
    assert resp.status_code == 200, resp.text
    assert resp.json()["created_count"] == 2

    listed = (await client.get("/api/items", headers=rt)).json()
    by_name = {i["name"]: i for i in listed["items"]}
    assert _tag_names_of(by_name["blade"]) == {"sharp"}
    assert _tag_names_of(by_name["wok"]) == {"kitchen", "heavy"}

async def test_import_location_path_creates_tree_and_legacy_columns_still_work(
    client, auth
):
    csv_bytes = _csv([
        "name,location_path",
        "牛奶,1F / 廚房 / 上櫃",
        "水餃,1F / 廚房 / 冰箱",
    ])
    files = {"file": ("items.csv", csv_bytes, "text/csv")}
    r = await client.post("/api/items/bulk-import", headers=auth, files=files)
    assert r.status_code == 200
    assert r.json()["created_count"] == 2

    locs = (await client.get("/api/locations", headers=auth)).json()
    assert [l["path"] for l in locs] == [
        "1F",
        "1F / 廚房",
        "1F / 廚房 / 上櫃",
        "1F / 廚房 / 冰箱",
    ]
    by_path = {l["path"]: l for l in locs}
    assert by_path["1F"]["kind"] == "floor"
    assert by_path["1F / 廚房"]["kind"] == "room"
    assert by_path["1F / 廚房 / 上櫃"]["kind"] == "other"

    # 舊檔三欄格式（Phase 26 前）相容：併為同一路徑
    legacy = _csv([
        "name,location_floor,location_room,location_zone",
        "雞蛋,2F,書房,抽屜",
    ])
    r2 = await client.post(
        "/api/items/bulk-import",
        headers=auth,
        files={"file": ("legacy.csv", legacy, "text/csv")},
    )
    assert r2.json()["created_count"] == 1
    locs2 = (await client.get("/api/locations", headers=auth)).json()
    assert "2F / 書房 / 抽屜" in {l["path"] for l in locs2}


async def test_export_import_roundtrip_preserves_location_path(client, auth):
    floor = (
        await client.post(
            "/api/locations", headers=auth, json={"name": "3F", "kind": "floor"}
        )
    ).json()
    room = (
        await client.post(
            "/api/locations",
            headers=auth,
            json={"name": "儲藏室", "parent_id": floor["id"], "kind": "room"},
        )
    ).json()
    await client.post(
        "/api/items",
        headers=auth,
        json={"name": "電池", "location_id": room["id"]},
    )

    exported = (await client.get("/api/items/export.csv", headers=auth)).text
    assert "3F / 儲藏室" in exported

    r = await client.post(
        "/api/items/bulk-import",
        headers=auth,
        files={"file": ("items.csv", exported.encode("utf-8"), "text/csv")},
    )
    assert r.json()["created_count"] == 1
    items = (await client.get("/api/items", headers=auth)).json()
    paths = {i["location"]["path"] for i in items["items"]}
    assert paths == {"3F / 儲藏室"}
