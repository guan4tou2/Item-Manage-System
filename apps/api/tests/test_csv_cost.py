from __future__ import annotations

import csv
import io

import pytest


@pytest.fixture
async def auth(client):
    await client.post(
        "/api/auth/register",
        json={"email": "csvc@t.io", "username": "csv_cost_user", "password": "secret1234"},
    )
    r = await client.post(
        "/api/auth/login",
        json={"username": "csv_cost_user", "password": "secret1234"},
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _import(client, auth, content: str):
    return await client.post(
        "/api/items/bulk-import",
        headers=auth,
        files={"file": ("items.csv", content.encode("utf-8"), "text/csv")},
    )


async def test_export_includes_cost_and_currency_columns(client, auth):
    await client.post(
        "/api/items", headers=auth, json={"name": "有價", "cost": "12.30"}
    )
    await client.post("/api/items", headers=auth, json={"name": "無價"})

    resp = await client.get("/api/items/export.csv", headers=auth)
    assert resp.status_code == 200
    rows = list(csv.DictReader(io.StringIO(resp.text)))
    header = list(rows[0].keys())
    assert header[header.index("min_quantity") + 1 : header.index("min_quantity") + 3] == [
        "cost",
        "currency",
    ]
    by_name = {r["name"]: r for r in rows}
    assert by_name["有價"]["cost"] == "12.30"
    assert by_name["有價"]["currency"] == "TWD"
    assert by_name["無價"]["cost"] == ""
    assert by_name["無價"]["currency"] == "TWD"


async def test_export_currency_follows_preference(client, auth):
    await client.post("/api/items", headers=auth, json={"name": "x", "cost": "1.00"})
    await client.put(
        "/api/users/me/preferences", headers=auth, json={"currency": "JPY"}
    )
    resp = await client.get("/api/items/export.csv", headers=auth)
    rows = list(csv.DictReader(io.StringIO(resp.text)))
    assert rows[0]["currency"] == "JPY"


async def test_import_sets_cost(client, auth):
    resp = await _import(
        client, auth, "name,quantity,cost\n咖啡豆,2,5.25\n濾紙,1,\n"
    )
    assert resp.status_code == 200
    assert resp.json()["created_count"] == 2
    items = (await client.get("/api/items", headers=auth)).json()["items"]
    by_name = {i["name"]: i for i in items}
    assert by_name["咖啡豆"]["cost"] == "5.25"
    assert by_name["濾紙"]["cost"] is None


async def test_import_rejects_invalid_cost(client, auth):
    resp = await _import(
        client,
        auth,
        "name,cost\n三小數,1.234\n負數,-1\n非數字,abc\n,5.00\n",
    )
    body = resp.json()
    assert body["created_count"] == 0
    assert len(body["errors"]) == 4
    reasons = {e["row"]: e["reason"] for e in body["errors"]}
    assert "cost" in reasons[2]
    assert "cost" in reasons[3]
    assert "cost" in reasons[4]
    # 空名稱優先於成本驗證
    assert reasons[5] == "name is required"


async def test_import_currency_mismatch_is_row_error(client, auth):
    resp = await _import(
        client,
        auth,
        'name,cost,currency\n美金價,9.99,USD\n台幣價,9.99,TWD\n空幣別,9.99,\n無欄位價,9.99\n',
    )
    body = resp.json()
    assert body["created_count"] == 3
    assert len(body["errors"]) == 1
    assert body["errors"][0]["row"] == 2
    assert "currency" in body["errors"][0]["reason"]


async def test_import_old_file_without_cost_columns_compatible(client, auth):
    resp = await _import(client, auth, "name,quantity\n舊檔物品,3\n")
    body = resp.json()
    assert body["created_count"] == 1
    assert body["errors"] == []
    item = (await client.get("/api/items?q=舊檔物品", headers=auth)).json()["items"][0]
    assert item["cost"] is None


async def test_round_trip_preserves_cost(client, auth):
    await client.post(
        "/api/items", headers=auth, json={"name": "匯出物品", "quantity": 2, "cost": "3.50"}
    )
    exported = (await client.get("/api/items/export.csv", headers=auth)).text

    await client.post(
        "/api/auth/register",
        json={"email": "csvc2@t.io", "username": "csv_cost_user2", "password": "secret1234"},
    )
    tok2 = (
        await client.post(
            "/api/auth/login",
            json={"username": "csv_cost_user2", "password": "secret1234"},
        )
    ).json()["access_token"]
    auth2 = {"Authorization": f"Bearer {tok2}"}

    resp = await _import(client, auth2, exported)
    assert resp.json()["created_count"] == 1
    items = (await client.get("/api/items", headers=auth2)).json()["items"]
    assert items[0]["name"] == "匯出物品"
    assert items[0]["cost"] == "3.50"
    assert items[0]["quantity"] == 2
