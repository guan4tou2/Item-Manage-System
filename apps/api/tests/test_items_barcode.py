from __future__ import annotations

import pytest


@pytest.fixture
async def auth(client):
    await client.post(
        "/api/auth/register",
        json={"email": "itembc@t.io", "username": "itembc_user", "password": "secret1234"},
    )
    r = await client.post(
        "/api/auth/login", json={"username": "itembc_user", "password": "secret1234"}
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def test_create_item_canonicalizes_barcode(client, auth):
    r = await client.post(
        "/api/items", headers=auth, json={"name": "書", "barcode": "978-0-306-40615-7"}
    )
    assert r.status_code == 201
    body = r.json()
    assert body["barcode"] == "9780306406157"

    again = (await client.get(f"/api/items/{body['id']}", headers=auth)).json()
    assert again["barcode"] == "9780306406157"


async def test_create_item_without_barcode_is_null(client, auth):
    r = await client.post("/api/items", headers=auth, json={"name": "無條碼"})
    assert r.status_code == 201
    assert r.json()["barcode"] is None


async def test_update_barcode_change_clear_and_untouched(client, auth):
    created = (
        await client.post(
            "/api/items",
            headers=auth,
            json={"name": "牛奶", "barcode": "4710085200016"},
        )
    ).json()

    changed = await client.patch(
        f"/api/items/{created['id']}", headers=auth, json={"barcode": "471-0085-200023"}
    )
    assert changed.json()["barcode"] == "4710085200023"

    untouched = await client.patch(
        f"/api/items/{created['id']}", headers=auth, json={"name": "牛奶改"}
    )
    assert untouched.json()["barcode"] == "4710085200023"

    cleared = await client.patch(
        f"/api/items/{created['id']}", headers=auth, json={"barcode": None}
    )
    assert cleared.json()["barcode"] is None


async def test_barcode_too_long_is_422(client, auth):
    r = await client.post(
        "/api/items", headers=auth, json={"name": "X", "barcode": "9" * 33}
    )
    assert r.status_code == 422


async def test_q_search_matches_barcode(client, auth):
    await client.post(
        "/api/items", headers=auth, json={"name": "鮮奶", "barcode": "4710085200016"}
    )
    await client.post("/api/items", headers=auth, json={"name": "其他物品"})

    r = await client.get("/api/items", headers=auth, params={"q": "4710085200016"})
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "鮮奶"


async def test_barcode_survives_bulk_update(client, auth):
    created = (
        await client.post(
            "/api/items",
            headers=auth,
            json={"name": "果汁", "barcode": "4710085200023"},
        )
    ).json()

    r = await client.patch(
        "/api/items/bulk", headers=auth, json={"item_ids": [created["id"]], "tag_names": ["飲料"]}
    )
    assert r.status_code == 200

    again = (await client.get(f"/api/items/{created['id']}", headers=auth)).json()
    assert again["barcode"] == "4710085200023"
