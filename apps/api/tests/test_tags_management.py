from __future__ import annotations

import pytest


@pytest.fixture
async def auth(client):
    await client.post(
        "/api/auth/register",
        json={"email": "tmgmt@t.io", "username": "tmgmt_user", "password": "secret1234"},
    )
    r = await client.post(
        "/api/auth/login",
        json={"username": "tmgmt_user", "password": "secret1234"},
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _seed_tags(client, auth) -> dict[str, dict]:
    """Create four tags via item-create side effects: kitchen (2 items),
    heavy (1 item), sharp (1 item), unused (0 items after deletions).

    Returns {name: tag_dict}.
    """
    # kitchen + heavy on one item
    await client.post(
        "/api/items",
        headers=auth,
        json={"name": "wok", "tag_names": ["kitchen", "heavy"]},
    )
    # kitchen on a second item (to test merge reassignment)
    await client.post(
        "/api/items",
        headers=auth,
        json={"name": "pan", "tag_names": ["kitchen"]},
    )
    # sharp on a third
    blade = await client.post(
        "/api/items",
        headers=auth,
        json={"name": "blade", "tag_names": ["sharp"]},
    )
    # create "unused" via item then detach by updating the item to empty tags
    await client.post(
        "/api/items",
        headers=auth,
        json={"name": "scratch", "tag_names": ["unused"]},
    )
    # clear the tags on "scratch" so "unused" becomes an orphan
    scratch_id = None
    listed = (await client.get("/api/items", headers=auth)).json()
    for item in listed["items"]:
        if item["name"] == "scratch":
            scratch_id = item["id"]
    assert scratch_id is not None
    await client.patch(
        f"/api/items/{scratch_id}", headers=auth, json={"tag_names": []}
    )

    rows = (await client.get("/api/tags/with-counts", headers=auth)).json()
    return {t["name"]: t for t in rows}


# ---- GET /api/tags/with-counts ----------------------------------------


async def test_with_counts_includes_orphans(client, auth):
    tags = await _seed_tags(client, auth)
    assert tags["kitchen"]["item_count"] == 2
    assert tags["heavy"]["item_count"] == 1
    assert tags["sharp"]["item_count"] == 1
    assert tags["unused"]["item_count"] == 0


async def test_with_counts_sorted_by_name(client, auth):
    await _seed_tags(client, auth)
    rows = (await client.get("/api/tags/with-counts", headers=auth)).json()
    names = [r["name"] for r in rows]
    assert names == sorted(names)


async def test_with_counts_requires_auth(client):
    r = await client.get("/api/tags/with-counts")
    assert r.status_code == 401


# ---- PATCH /api/tags/{id} — rename ------------------------------------


async def test_rename_happy_path(client, auth):
    tags = await _seed_tags(client, auth)
    kitchen_id = tags["kitchen"]["id"]
    r = await client.patch(
        f"/api/tags/{kitchen_id}", headers=auth, json={"name": "cookware"}
    )
    assert r.status_code == 200
    assert r.json()["name"] == "cookware"


async def test_rename_lowercases_and_trims(client, auth):
    tags = await _seed_tags(client, auth)
    sharp_id = tags["sharp"]["id"]
    r = await client.patch(
        f"/api/tags/{sharp_id}", headers=auth, json={"name": "  BLADED  "}
    )
    assert r.status_code == 200
    assert r.json()["name"] == "bladed"


async def test_rename_conflict_returns_409(client, auth):
    tags = await _seed_tags(client, auth)
    sharp_id = tags["sharp"]["id"]
    r = await client.patch(
        f"/api/tags/{sharp_id}", headers=auth, json={"name": "kitchen"}
    )
    assert r.status_code == 409


async def test_rename_to_same_name_is_noop(client, auth):
    tags = await _seed_tags(client, auth)
    sharp_id = tags["sharp"]["id"]
    r = await client.patch(
        f"/api/tags/{sharp_id}", headers=auth, json={"name": "sharp"}
    )
    assert r.status_code == 200
    assert r.json()["name"] == "sharp"


async def test_rename_unknown_tag_404(client, auth):
    r = await client.patch("/api/tags/999999", headers=auth, json={"name": "x"})
    assert r.status_code == 404


async def test_rename_cross_owner_404(client, auth):
    tags = await _seed_tags(client, auth)
    kitchen_id = tags["kitchen"]["id"]
    # register another owner
    await client.post(
        "/api/auth/register",
        json={"email": "other@t.io", "username": "other_tag", "password": "secret1234"},
    )
    r = await client.post(
        "/api/auth/login", json={"username": "other_tag", "password": "secret1234"}
    )
    other = {"Authorization": f"Bearer {r.json()['access_token']}"}
    # other user tries to rename owner1's tag
    resp = await client.patch(
        f"/api/tags/{kitchen_id}", headers=other, json={"name": "stolen"}
    )
    assert resp.status_code == 404


# ---- POST /api/tags/{source}/merge ------------------------------------


async def test_merge_reassigns_items_and_deletes_source(client, auth):
    tags = await _seed_tags(client, auth)
    kitchen_id = tags["kitchen"]["id"]
    heavy_id = tags["heavy"]["id"]
    # merge heavy → kitchen
    r = await client.post(
        f"/api/tags/{heavy_id}/merge",
        headers=auth,
        json={"target_id": kitchen_id},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["target_id"] == kitchen_id
    # "wok" had both kitchen AND heavy — this is an overlap, reassignable = 0
    # (the heavy→kitchen row is dropped because kitchen is already attached)
    assert body["reassigned_item_count"] == 0

    # heavy tag is gone
    rows = (await client.get("/api/tags/with-counts", headers=auth)).json()
    names = {r["name"] for r in rows}
    assert "heavy" not in names
    # kitchen still has 2 items (unchanged — wok still has it, pan still has it)
    kitchen = next(r for r in rows if r["name"] == "kitchen")
    assert kitchen["item_count"] == 2


async def test_merge_reassigns_non_overlapping_items(client, auth):
    tags = await _seed_tags(client, auth)
    sharp_id = tags["sharp"]["id"]
    kitchen_id = tags["kitchen"]["id"]
    # merge sharp → kitchen. "blade" had sharp but NOT kitchen.
    r = await client.post(
        f"/api/tags/{sharp_id}/merge",
        headers=auth,
        json={"target_id": kitchen_id},
    )
    assert r.status_code == 200
    assert r.json()["reassigned_item_count"] == 1

    rows = (await client.get("/api/tags/with-counts", headers=auth)).json()
    kitchen = next(r for r in rows if r["name"] == "kitchen")
    # originally 2, + 1 reassigned from sharp = 3
    assert kitchen["item_count"] == 3


async def test_merge_self_rejects_400(client, auth):
    tags = await _seed_tags(client, auth)
    kitchen_id = tags["kitchen"]["id"]
    r = await client.post(
        f"/api/tags/{kitchen_id}/merge",
        headers=auth,
        json={"target_id": kitchen_id},
    )
    assert r.status_code == 400


async def test_merge_missing_source_404(client, auth):
    tags = await _seed_tags(client, auth)
    kitchen_id = tags["kitchen"]["id"]
    r = await client.post(
        "/api/tags/999999/merge",
        headers=auth,
        json={"target_id": kitchen_id},
    )
    assert r.status_code == 404


async def test_merge_missing_target_404(client, auth):
    tags = await _seed_tags(client, auth)
    kitchen_id = tags["kitchen"]["id"]
    r = await client.post(
        f"/api/tags/{kitchen_id}/merge",
        headers=auth,
        json={"target_id": 999999},
    )
    assert r.status_code == 404


# ---- DELETE /api/tags/{id} --------------------------------------------


async def test_delete_orphan_tag_ok(client, auth):
    tags = await _seed_tags(client, auth)
    unused_id = tags["unused"]["id"]
    r = await client.delete(f"/api/tags/{unused_id}", headers=auth)
    assert r.status_code == 204


async def test_delete_tag_with_items_conflicts(client, auth):
    tags = await _seed_tags(client, auth)
    kitchen_id = tags["kitchen"]["id"]
    r = await client.delete(f"/api/tags/{kitchen_id}", headers=auth)
    assert r.status_code == 409
    # still exists
    rows = (await client.get("/api/tags/with-counts", headers=auth)).json()
    assert any(r["name"] == "kitchen" for r in rows)


async def test_delete_tag_with_items_force(client, auth):
    tags = await _seed_tags(client, auth)
    kitchen_id = tags["kitchen"]["id"]
    r = await client.delete(
        f"/api/tags/{kitchen_id}?force=true", headers=auth
    )
    assert r.status_code == 204
    rows = (await client.get("/api/tags/with-counts", headers=auth)).json()
    assert not any(r["name"] == "kitchen" for r in rows)


# ---- POST /api/tags/prune-orphans -------------------------------------


async def test_prune_orphans_deletes_only_unused(client, auth):
    tags = await _seed_tags(client, auth)
    r = await client.post("/api/tags/prune-orphans", headers=auth)
    assert r.status_code == 200
    assert r.json()["deleted_count"] == 1
    rows = (await client.get("/api/tags/with-counts", headers=auth)).json()
    names = {t["name"] for t in rows}
    assert "unused" not in names
    assert {"kitchen", "heavy", "sharp"} <= names


async def test_prune_orphans_idempotent(client, auth):
    await _seed_tags(client, auth)
    await client.post("/api/tags/prune-orphans", headers=auth)
    # second call finds nothing
    r = await client.post("/api/tags/prune-orphans", headers=auth)
    assert r.status_code == 200
    assert r.json()["deleted_count"] == 0
