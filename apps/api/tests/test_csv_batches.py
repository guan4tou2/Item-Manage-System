from __future__ import annotations

import csv
import io
from datetime import timedelta

import pytest

from app.clock import today_taipei


@pytest.fixture
async def auth(client):
    await client.post("/api/auth/register", json={
        "email": "csvb@t.io", "username": "csvb_user", "password": "secret1234",
    })
    r = await client.post("/api/auth/login", json={
        "username": "csvb_user", "password": "secret1234",
    })
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def test_bulk_import_never_updates_tracked_items(client, auth):
    # tracked 物品：現有數量併入第一批
    item = (
        await client.post(
            "/api/items", headers=auth, json={"name": "牛奶", "quantity": 5}
        )
    ).json()
    await client.post(f"/api/items/{item['id']}/batches", headers=auth, json={})

    csv_bytes = "name,quantity\n牛奶,9\n新物,2\n".encode("utf-8")
    resp = await client.post(
        "/api/items/bulk-import",
        headers=auth,
        files={"file": ("items.csv", csv_bytes, "text/csv")},
    )
    assert resp.status_code == 200
    assert resp.json()["created_count"] == 2
    assert resp.json()["errors"] == []

    # 原 tracked 物品未被匯入改寫（匯入只建新物品，無 match-update 路徑）
    fresh = (await client.get(f"/api/items/{item['id']}", headers=auth)).json()
    assert fresh["quantity"] == 5
    assert fresh["track_batches"] is True
    batches = (
        await client.get(f"/api/items/{item['id']}/batches", headers=auth)
    ).json()
    assert len(batches) == 1
    assert batches[0]["quantity"] == 5
    # invariant 仍成立（roadmap 驗收 2）
    assert sum(b["quantity"] for b in batches if not b["is_depleted"]) == fresh["quantity"]

    # 匯入建立的是新物品，且為 untracked
    listed = (await client.get("/api/items?q=牛奶", headers=auth)).json()["items"]
    assert len(listed) == 2
    new_item = next(i for i in listed if i["id"] != item["id"])
    assert new_item["track_batches"] is False
    assert new_item["quantity"] == 9
    assert new_item["soonest_expiry"] is None


async def test_export_csv_expiry_column_for_single_active_batch(client, auth):
    # 恰一筆未耗盡批次 → 帶到期日
    a = (
        await client.post("/api/items", headers=auth, json={"name": "A", "quantity": 1})
    ).json()
    exp = (today_taipei() + timedelta(days=10)).isoformat()
    resp = await client.post(
        f"/api/items/{a['id']}/batches", headers=auth, json={"expiry_date": exp}
    )
    assert resp.status_code == 201

    # 兩筆批次 → 留空
    b = (
        await client.post("/api/items", headers=auth, json={"name": "B", "quantity": 1})
    ).json()
    await client.post(f"/api/items/{b['id']}/batches", headers=auth, json={})
    await client.post(
        f"/api/items/{b['id']}/batches", headers=auth, json={"quantity": 1}
    )

    # 未追蹤 → 留空
    await client.post("/api/items", headers=auth, json={"name": "C", "quantity": 3})

    resp = await client.get("/api/items/export.csv", headers=auth)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    rows = list(csv.DictReader(io.StringIO(resp.text)))
    assert list(rows[0].keys())[-1] == "expiry_date"
    by_name = {r["name"]: r for r in rows}
    assert by_name["A"]["expiry_date"] == exp
    assert by_name["B"]["expiry_date"] == ""
    assert by_name["C"]["expiry_date"] == ""


async def test_export_csv_requires_auth(client):
    resp = await client.get("/api/items/export.csv")
    assert resp.status_code == 401
