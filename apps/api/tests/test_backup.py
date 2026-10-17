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
    assert body["format_version"] == 4
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

    assert body["format_version"] == 4
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


# --- Phase 29：v4 全量匯出 ---


async def test_export_v4_new_keys_on_empty_account(client, auth):
    body = (await client.get("/api/backup/export", headers=auth)).json()
    assert body["format_version"] == 4
    for key in (
        "item_custom_values",
        "item_batches",
        "loans",
        "quantity_logs",
        "item_versions",
        "stocktakes",
        "webhooks",
        "notification_preferences",
    ):
        assert body[key] == [], key
    assert body["preferences"] == {"currency": "TWD"}


async def test_export_items_include_barcode_and_track_batches(client, auth):
    await client.post(
        "/api/items", headers=auth, json={"name": "掃碼", "barcode": "4711234567890"}
    )
    item = (
        await client.post("/api/items", headers=auth, json={"name": "批次", "quantity": 1})
    ).json()
    await client.post(
        f"/api/items/{item['id']}/batches",
        headers=auth,
        json={"quantity": 2, "expiry_date": "2026-01-15"},
    )
    body = (await client.get("/api/backup/export", headers=auth)).json()
    by_name = {i["name"]: i for i in body["items"]}
    assert by_name["掃碼"]["barcode"] == "4711234567890"
    assert by_name["掃碼"]["track_batches"] is False
    assert by_name["批次"]["track_batches"] is True


async def test_export_includes_batches_with_depleted(client, auth):
    item = (
        await client.post("/api/items", headers=auth, json={"name": "批", "quantity": 1})
    ).json()
    b1 = (
        await client.post(
            f"/api/items/{item['id']}/batches",
            headers=auth,
            json={
                "quantity": 2,
                "expiry_date": "2026-01-15",
                "received_at": "2026-01-02",
                "note": "n",
            },
        )
    ).json()
    b2 = (
        await client.post(
            f"/api/items/{item['id']}/batches", headers=auth, json={"quantity": 4}
        )
    ).json()
    await client.post(
        f"/api/items/{item['id']}/batches/{b2['id']}/consume",
        headers=auth,
        json={"quantity": 4},
    )
    body = (await client.get("/api/backup/export", headers=auth)).json()
    assert len(body["item_batches"]) == 2
    by_id = {b["id"]: b for b in body["item_batches"]}
    assert by_id[b1["id"]]["quantity"] == 2
    assert by_id[b1["id"]]["expiry_date"] == "2026-01-15"
    assert by_id[b1["id"]]["received_at"] == "2026-01-02"
    assert by_id[b1["id"]]["note"] == "n"
    assert by_id[b1["id"]]["is_depleted"] is False
    assert by_id[b2["id"]]["is_depleted"] is True


async def test_export_includes_loans_and_quantity_logs(client, auth):
    item = (
        await client.post("/api/items", headers=auth, json={"name": "借", "quantity": 5})
    ).json()
    await client.post(
        f"/api/items/{item['id']}/loans",
        headers=auth,
        json={"borrower_label": "小明", "expected_return": "2026-03-01"},
    )
    await client.patch(f"/api/items/{item['id']}", headers=auth, json={"quantity": 3})
    body = (await client.get("/api/backup/export", headers=auth)).json()
    assert len(body["loans"]) == 1
    loan = body["loans"][0]
    assert loan["item_id"] == item["id"]
    assert loan["borrower_label"] == "小明"
    assert loan["borrower_user_id"] is None
    assert loan["expected_return"] == "2026-03-01"
    assert loan["returned_at"] is None
    assert any(
        log["old_quantity"] == 5 and log["new_quantity"] == 3
        for log in body["quantity_logs"]
    )


async def test_export_includes_item_versions(client, auth):
    item = (await client.post("/api/items", headers=auth, json={"name": "版"})).json()
    await client.patch(f"/api/items/{item['id']}", headers=auth, json={"name": "新版"})
    body = (await client.get("/api/backup/export", headers=auth)).json()
    assert len(body["item_versions"]) >= 1
    version = body["item_versions"][-1]
    assert version["item_id"] == item["id"]
    assert isinstance(version["snapshot"], dict)


async def test_export_includes_custom_values(client, auth):
    field = (
        await client.post(
            "/api/custom-fields",
            headers=auth,
            json={"name": "尺寸", "field_type": "text"},
        )
    ).json()
    item = (await client.post("/api/items", headers=auth, json={"name": "值"})).json()
    await client.post(
        f"/api/items/{item['id']}/custom-values",
        headers=auth,
        json={"custom_field_id": field["id"], "value": "L"},
    )
    body = (await client.get("/api/backup/export", headers=auth)).json()
    assert body["item_custom_values"] == [
        {"item_id": item["id"], "custom_field_id": field["id"], "value": {"v": "L"}}
    ]


async def test_export_includes_stocktakes(client, auth):
    item = (
        await client.post("/api/items", headers=auth, json={"name": "盤", "quantity": 3})
    ).json()
    st = (
        await client.post("/api/stocktakes", headers=auth, json={"name": "Q1"})
    ).json()
    await client.post(
        f"/api/stocktakes/{st['id']}/scan",
        headers=auth,
        json={"item_id": item["id"], "actual_quantity": 2, "note": "少一"},
    )
    body = (await client.get("/api/backup/export", headers=auth)).json()
    assert len(body["stocktakes"]) == 1
    s = body["stocktakes"][0]
    assert s["name"] == "Q1"
    assert s["status"] == "open"
    assert len(s["items"]) == 1
    assert s["items"][0]["expected_quantity"] == 3
    assert s["items"][0]["actual_quantity"] == 2
    assert s["items"][0]["note"] == "少一"


async def test_export_includes_webhooks(client, auth):
    await client.post(
        "/api/webhooks",
        headers=auth,
        json={
            "name": "w",
            "url": "https://example.com/hook",
            "secret": "s3cret",
            "events": ["item.created"],
        },
    )
    body = (await client.get("/api/backup/export", headers=auth)).json()
    assert len(body["webhooks"]) == 1
    w = body["webhooks"][0]
    assert w["url"] == "https://example.com/hook"
    assert w["secret"] == "s3cret"
    assert w["events"] == ["item.created"]
    assert w["is_active"] is True


async def test_export_includes_notification_preferences(client, auth):
    r = await client.put(
        "/api/notifications/preferences",
        headers=auth,
        json={"updates": [{"type": "low_stock", "channel": "email", "enabled": False}]},
    )
    assert r.status_code == 200
    body = (await client.get("/api/backup/export", headers=auth)).json()
    assert body["notification_preferences"] == [
        {"type": "low_stock", "channel": "email", "enabled": False}
    ]


async def test_export_includes_currency_preference(client, auth):
    r = await client.put(
        "/api/users/me/preferences", headers=auth, json={"currency": "USD"}
    )
    assert r.status_code == 200
    body = (await client.get("/api/backup/export", headers=auth)).json()
    assert body["preferences"] == {"currency": "USD"}


async def test_export_dates_are_iso_strings(client, auth):
    await client.post(
        "/api/lists",
        headers=auth,
        json={
            "kind": "generic",
            "title": "d",
            "start_date": "2026-01-01",
            "end_date": "2026-02-01",
        },
    )
    r = await client.get("/api/backup/export", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["lists"][0]["start_date"] == "2026-01-01"
    assert body["lists"][0]["end_date"] == "2026-02-01"
