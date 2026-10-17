from __future__ import annotations

import json

import pytest


@pytest.fixture
async def auth(client):
    await client.post(
        "/api/auth/register",
        json={"email": "i@t.io", "username": "i_user", "password": "secret1234"},
    )
    r = await client.post(
        "/api/auth/login", json={"username": "i_user", "password": "secret1234"}
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _payload(*, raw: bytes | None = None, doc: dict | None = None) -> dict:
    body = raw if raw is not None else json.dumps(doc or {}).encode("utf-8")
    return {"file": ("backup.json", body, "application/json")}


async def _post(
    client,
    auth,
    *,
    doc: dict | None = None,
    raw: bytes | None = None,
    mode: str | None = None,
    dry_run: bool | None = True,
    confirm: str | None = None,
):
    data: dict[str, str] = {}
    if mode is not None:
        data["mode"] = mode
    if dry_run is not None:
        data["dry_run"] = "true" if dry_run else "false"
    if confirm is not None:
        data["confirm"] = confirm
    return await client.post(
        "/api/backup/import", headers=auth, files=_payload(raw=raw, doc=doc), data=data
    )


def _item(name: str, *, item_id: str = "11111111-1111-1111-1111-111111111111", **extra):
    return {"id": item_id, "name": name, "quantity": 1, **extra}


# ---- 檔案層級硬錯誤 ----


async def test_import_rejects_invalid_json(client, auth):
    r = await _post(client, auth, raw=b"{ not json")
    assert r.status_code == 400
    assert "JSON" in r.json()["detail"]


async def test_import_rejects_root_not_object(client, auth):
    r = await _post(client, auth, doc=None, raw=json.dumps([1, 2]).encode())
    assert r.status_code == 400
    assert "物件" in r.json()["detail"]


async def test_import_rejects_missing_format_version(client, auth):
    r = await _post(client, auth, doc={})
    assert r.status_code == 400
    assert "format_version" in r.json()["detail"]


async def test_import_rejects_future_format_version(client, auth):
    r = await _post(client, auth, doc={"format_version": 5})
    assert r.status_code == 400
    assert "高於" in r.json()["detail"]


async def test_import_rejects_zero_format_version(client, auth):
    r = await _post(client, auth, doc={"format_version": 0})
    assert r.status_code == 400


async def test_import_rejects_non_list_entity(client, auth):
    r = await _post(client, auth, doc={"format_version": 4, "items": {}})
    assert r.status_code == 400
    assert "陣列" in r.json()["detail"]


async def test_import_rejects_oversized_file(client, auth, monkeypatch):
    from app.services import backup_import_service

    monkeypatch.setattr(backup_import_service, "MAX_BACKUP_BYTES", 64)
    r = await _post(client, auth, doc={"format_version": 4, "items": [_item("x" * 200)]})
    assert r.status_code == 413
    assert "上限" in r.json()["detail"]


async def test_import_rejects_unknown_mode(client, auth):
    r = await _post(client, auth, doc={"format_version": 4}, mode="merge")
    assert r.status_code == 422


# ---- replace 的 confirm 契約（在 plan/apply 之前擋下） ----


async def test_replace_requires_confirm_phrase(client, auth):
    r = await _post(
        client, auth, doc={"format_version": 4}, mode="replace", dry_run=False
    )
    assert r.status_code == 400
    assert "REPLACE" in r.json()["detail"]

    r = await _post(
        client, auth, doc={"format_version": 4}, mode="replace", dry_run=False, confirm="WRONG"
    )
    assert r.status_code == 400


async def test_replace_dry_run_needs_no_confirm(client, auth):
    r = await _post(client, auth, doc={"format_version": 4}, mode="replace", dry_run=True)
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "replace"
    assert body["deleted_total"] == 0


# ---- dry-run 摘要 ----


async def test_import_empty_backup_dry_run_ok(client, auth):
    r = await _post(client, auth, doc={"format_version": 4})
    assert r.status_code == 200
    body = r.json()
    assert body["format_version"] == 4
    assert body["mode"] == "create_only"
    assert body["dry_run"] is True
    assert body["status"] == "ok"
    assert body["errors"] == []
    assert body["errors_total"] == 0
    assert body["deleted_total"] == 0
    assert body["reconciliation"] == []
    # preferences 恆存在 → 至少一列；create_only → 略過（不覆蓋幣別）
    prefs = next(e for e in body["entities"] if e["entity"] == "preferences")
    assert prefs["existing"] == 1
    assert prefs["skipped"] == 1


async def test_import_dry_run_writes_nothing(client, auth):
    doc = {
        "format_version": 4,
        "items": [_item("乾糧")],
        "categories": [{"id": 1, "name": "食物", "parent_id": None}],
        "tags": [{"id": 1, "name": "儲備"}],
        "warehouses": [{"id": 1, "name": "家"}],
        "webhooks": [{"name": "w", "url": "https://example.com/h", "events": ["item.created"]}],
        "groups_owned": [{"id": "22222222-2222-2222-2222-222222222222", "name": "家人"}],
        "notification_preferences": [
            {"type": "low_stock", "channel": "email", "enabled": False}
        ],
    }
    r = await _post(client, auth, doc=doc)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

    exported = (await client.get("/api/backup/export", headers=auth)).json()
    for key in (
        "items",
        "categories",
        "tags",
        "warehouses",
        "webhooks",
        "groups_owned",
        "notification_preferences",
        "item_batches",
    ):
        assert exported[key] == [], key


async def test_import_dry_run_summary_counts_partial(client, auth):
    doc = {
        "format_version": 4,
        "items": [_item("好的"), {"id": "33333333-3333-3333-3333-333333333333", "name": "  "}],
        "tags": [{"id": 1, "name": "標"}],
    }
    r = await _post(client, auth, doc=doc)
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "partial"
    assert body["errors_total"] == 1
    error = body["errors"][0]
    assert error["entity"] == "items"
    assert error["index"] == 1
    items = next(e for e in body["entities"] if e["entity"] == "items")
    assert items["imported"] == 2
    assert items["created"] == 1
    assert items["errors"] == 1
    tags = next(e for e in body["entities"] if e["entity"] == "tags")
    assert tags["imported"] == 1 and tags["created"] == 1


async def test_import_v3_file_tolerated(client, auth):
    doc = {
        "format_version": 3,
        "items": [{"id": "44444444-4444-4444-4444-444444444444", "name": "舊檔", "quantity": 2}],
    }
    r = await _post(client, auth, doc=doc)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    items = next(e for e in body["entities"] if e["entity"] == "items")
    assert items["created"] == 1


async def test_import_unknown_reference_yields_warning(client, auth):
    doc = {
        "format_version": 4,
        "items": [_item("孤兒", category_id=99)],
    }
    r = await _post(client, auth, doc=doc)
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "ok"
    assert any("參照不存在" in w for w in body["warnings"])


async def test_import_reconciliation_reports_mismatch(client, auth):
    doc = {
        "format_version": 4,
        "items": [_item("批", quantity=5, track_batches=True)],
        "item_batches": [
            {
                "id": "55555555-5555-5555-5555-555555555555",
                "item_id": "11111111-1111-1111-1111-111111111111",
                "quantity": 3,
                "is_depleted": False,
            },
            {
                "id": "66666666-6666-6666-6666-666666666666",
                "item_id": "11111111-1111-1111-1111-111111111111",
                "quantity": 9,
                "is_depleted": True,
            },
        ],
    }
    r = await _post(client, auth, doc=doc)
    body = r.json()
    assert r.status_code == 200
    assert len(body["reconciliation"]) == 1
    entry = body["reconciliation"][0]
    assert entry["name"] == "批"
    assert entry["quantity"] == 5
    assert entry["batch_total"] == 3
    assert any("不一致" in w for w in body["warnings"])

    # 實際匯入亦回報（且批次以備份值落檔）
    r2 = await _post(client, auth, doc=doc, dry_run=False)
    assert r2.status_code == 200
    assert len(r2.json()["reconciliation"]) == 1
    exported = (await client.get("/api/backup/export", headers=auth)).json()
    assert sorted(b["quantity"] for b in exported["item_batches"]) == [3, 9]
    assert exported["items"][0]["quantity"] == 5


async def test_import_entity_summary_partition(client, auth):
    doc = {
        "format_version": 4,
        "items": [_item("a")],
        "tags": [{"id": 1, "name": "t"}, {"id": 2, "name": "t2"}],
        "categories": [
            {"id": 1, "name": "c1", "parent_id": None},
            {"id": 2, "name": "c2", "parent_id": 1},
        ],
    }
    body = (await _post(client, auth, doc=doc)).json()
    for entity in body["entities"]:
        assert (
            entity["created"]
            + entity["reused"]
            + entity["renamed"]
            + entity["skipped"]
            + entity["errors"]
            == entity["imported"]
        ), entity


# ---------------------------------------------------------------------------
# T1.3：apply（create_only／replace 於空帳號）與 round-trip 等價
# ---------------------------------------------------------------------------


async def _register(client, username: str) -> dict:
    await client.post(
        "/api/auth/register",
        json={"email": f"{username}@t.io", "username": username, "password": "secret1234"},
    )
    r = await client.post(
        "/api/auth/login", json={"username": username, "password": "secret1234"}
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _seed_full_account(client, auth) -> None:
    """建立涵蓋可還原實體的帳號資料（round-trip 用）。"""
    await client.post(
        "/api/auth/register",
        json={"email": "b2@t.io", "username": "b_borrower", "password": "secret1234"},
    )

    food = (await client.post("/api/categories", headers=auth, json={"name": "食物"})).json()
    await client.post(
        "/api/categories", headers=auth, json={"name": "乾糧", "parent_id": food["id"]}
    )
    floor = (
        await client.post("/api/locations", headers=auth, json={"name": "1F", "kind": "floor"})
    ).json()
    await client.post(
        "/api/locations",
        headers=auth,
        json={"name": "廚房", "parent_id": floor["id"], "kind": "room"},
    )
    wh = (
        await client.post("/api/warehouses", headers=auth, json={"name": "家", "description": "主要倉"})
    ).json()
    await client.post("/api/item-types", headers=auth, json={"name": "食品", "icon": "apple"})
    field = (
        await client.post(
            "/api/custom-fields", headers=auth, json={"name": "尺寸", "field_type": "text"}
        )
    ).json()
    await client.post(
        "/api/item-templates",
        headers=auth,
        json={"name": "常用", "payload": {"name": "範本", "quantity": 2}},
    )

    rice = (
        await client.post(
            "/api/items",
            headers=auth,
            json={
                "name": "白米",
                "description": "台灣米",
                "quantity": 2,
                "min_quantity": 1,
                "cost": "120.50",
                "barcode": "4711234567890",
                "category_id": food["id"],
                "location_id": floor["id"],
                "warehouse_id": wh["id"],
                "tag_names": ["儲備"],
            },
        )
    ).json()
    await client.post(
        f"/api/items/{rice['id']}/custom-values",
        headers=auth,
        json={"custom_field_id": field["id"], "value": "L"},
    )
    await client.patch(
        f"/api/items/{rice['id']}", headers=auth, json={"quantity": 3, "notes": "已補貨"}
    )

    battery = (
        await client.post(
            "/api/items", headers=auth, json={"name": "電池", "quantity": 4, "cost": "55.00"}
        )
    ).json()
    await client.post(
        f"/api/items/{battery['id']}/batches",
        headers=auth,
        json={"quantity": 2, "expiry_date": "2027-01-15", "received_at": "2026-02-01", "note": "新"},
    )
    b2 = (
        await client.post(
            f"/api/items/{battery['id']}/batches", headers=auth, json={"quantity": 2}
        )
    ).json()
    await client.post(
        f"/api/items/{battery['id']}/batches/{b2['id']}/consume",
        headers=auth,
        json={"quantity": 2},
    )
    await client.post(
        f"/api/items/{battery['id']}/loans",
        headers=auth,
        json={"borrower_username": "b_borrower", "expected_return": "2026-03-01", "notes": "借一支"},
    )

    lst = (
        await client.post(
            "/api/lists",
            headers=auth,
            json={
                "kind": "generic",
                "title": "採購",
                "budget": "500.00",
                "start_date": "2026-01-01",
                "end_date": "2026-02-01",
            },
        )
    ).json()
    await client.post(
        f"/api/lists/{lst['id']}/entries",
        headers=auth,
        json={"name": "米", "quantity": 2, "price": "99.50", "link": "https://example.com/m"},
    )
    await client.post(
        f"/api/lists/{lst['id']}/entries", headers=auth, json={"name": "電", "position": 1}
    )

    stocktake = (await client.post("/api/stocktakes", headers=auth, json={"name": "Q1"})).json()
    await client.post(
        f"/api/stocktakes/{stocktake['id']}/scan",
        headers=auth,
        json={"item_id": rice["id"], "actual_quantity": 1, "note": "少一"},
    )

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
    r = await client.put(
        "/api/notifications/preferences",
        headers=auth,
        json={"updates": [{"type": "low_stock", "channel": "email", "enabled": False}]},
    )
    assert r.status_code == 200
    await client.put("/api/users/me/preferences", headers=auth, json={"currency": "USD"})
    await client.post("/api/groups", headers=auth, json={"name": "家人"})


def _norm_export(doc: dict) -> dict:
    """正規化匯出內容：以名稱／路徑取代 id 後逐實體比對。"""
    cats = {c["id"]: c for c in doc["categories"]}
    locs = {l["id"]: l for l in doc["locations"]}
    tags = {t["id"]: t for t in doc["tags"]}
    whs = {w["id"]: w for w in doc["warehouses"]}
    fields = {f["id"]: f for f in doc["custom_fields"]}
    items = {i["id"]: i for i in doc["items"]}

    def _tree_path(by_id, node_id):
        parts: list[str] = []
        seen: set = set()
        while node_id is not None and node_id in by_id and node_id not in seen:
            seen.add(node_id)
            parts.append(by_id[node_id]["name"])
            node_id = by_id[node_id]["parent_id"]
        return "/".join(reversed(parts))

    def _item_name(item_id):
        return items[item_id]["name"] if item_id in items else None

    def _ref_name(by_id, ref_id):
        return by_id[ref_id]["name"] if ref_id in by_id else None

    def _payload(value):
        return json.dumps(value, sort_keys=True, ensure_ascii=False)

    return {
        "format_version": doc["format_version"],
        "preferences": doc["preferences"],
        "items": sorted(
            (
                i["name"],
                i["description"],
                i["notes"],
                i["barcode"],
                i["quantity"],
                i["min_quantity"],
                i["cost"],
                i["track_batches"],
                i["is_favorite"],
                _tree_path(cats, i["category_id"]),
                _tree_path(locs, i["location_id"]),
                _ref_name(whs, i["warehouse_id"]),
                tuple(sorted(i["tag_names"])),
            )
            for i in doc["items"]
        ),
        "categories": sorted(_tree_path(cats, c["id"]) for c in doc["categories"]),
        "locations": sorted(
            (_tree_path(locs, loc["id"]), loc["kind"]) for loc in doc["locations"]
        ),
        "tags": sorted(t["name"] for t in doc["tags"]),
        "warehouses": sorted((w["name"], w["description"]) for w in doc["warehouses"]),
        "item_types": sorted((t["name"], t["icon"]) for t in doc["item_types"]),
        "custom_fields": sorted((f["name"], f["field_type"]) for f in doc["custom_fields"]),
        "item_templates": sorted((t["name"], _payload(t["payload"])) for t in doc["item_templates"]),
        "item_custom_values": sorted(
            (
                _item_name(v["item_id"]),
                _ref_name(fields, v["custom_field_id"]),
                _payload(v["value"]),
            )
            for v in doc["item_custom_values"]
        ),
        "item_batches": sorted(
            (
                _item_name(b["item_id"]),
                b["quantity"],
                b["expiry_date"],
                b["received_at"],
                b["note"],
                b["is_depleted"],
            )
            for b in doc["item_batches"]
        ),
        "loans": sorted(
            (
                _item_name(loan["item_id"]),
                loan["borrower_label"],
                loan["borrower_user_id"],
                loan["expected_return"],
                loan["returned_at"] is not None,
                loan["notes"],
            )
            for loan in doc["loans"]
        ),
        "quantity_logs": sorted(
            (_item_name(log["item_id"]), log["old_quantity"], log["new_quantity"], log["reason"])
            for log in doc["quantity_logs"]
        ),
        "item_versions": sorted(
            (_item_name(v["item_id"]), _payload(v["snapshot"])) for v in doc["item_versions"]
        ),
        "lists": sorted(
            (
                lst["kind"],
                lst["title"],
                lst["description"],
                lst["start_date"],
                lst["end_date"],
                lst["budget"],
                tuple(
                    sorted(
                        (
                            e["position"],
                            e["name"],
                            e["quantity"],
                            e["note"],
                            e["price"],
                            e["link"],
                            e["is_done"],
                        )
                        for e in lst["entries"]
                    )
                ),
            )
            for lst in doc["lists"]
        ),
        "stocktakes": sorted(
            (
                st["name"],
                st["status"],
                tuple(
                    sorted(
                        (
                            _item_name(x["item_id"]),
                            x["expected_quantity"],
                            x["actual_quantity"],
                            x["note"],
                        )
                        for x in st["items"]
                    )
                ),
            )
            for st in doc["stocktakes"]
        ),
        "webhooks": sorted(
            (w["name"], w["url"], w["secret"], tuple(w["events"])) for w in doc["webhooks"]
        ),
        "notification_preferences": sorted(
            (p["type"], p["channel"], p["enabled"]) for p in doc["notification_preferences"]
        ),
        "groups_owned": sorted(g["name"] for g in doc["groups_owned"]),
    }


async def test_replace_round_trip_equivalent(client, auth):
    await _seed_full_account(client, auth)
    doc_a = (await client.get("/api/backup/export", headers=auth)).json()

    auth_c = await _register(client, "c_user")
    r = await _post(client, auth_c, doc=doc_a, mode="replace", dry_run=False, confirm="REPLACE")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok", body["errors"]
    assert body["dry_run"] is False
    assert body["deleted_total"] == 0  # 空帳號

    doc_c = (await client.get("/api/backup/export", headers=auth_c)).json()
    assert _norm_export(doc_c) == _norm_export(doc_a)
    assert doc_c["preferences"] == {"currency": "USD"}
    # webhooks 一律停用還原
    assert doc_c["webhooks"] and all(w["is_active"] is False for w in doc_c["webhooks"])
    # 通知偏好逐格還原
    assert _norm_export(doc_c)["notification_preferences"] == [("low_stock", "email", False)]

    # 對帳 invariant：track_batches 物品 quantity == Σ 未耗盡批次
    batch_totals: dict = {}
    for b in doc_c["item_batches"]:
        if not b["is_depleted"]:
            batch_totals[b["item_id"]] = batch_totals.get(b["item_id"], 0) + b["quantity"]
    for item in doc_c["items"]:
        if item["track_batches"]:
            assert item["quantity"] == batch_totals.get(item["id"], 0), item["name"]
    assert batch_totals  # 至少一件批次物品被檢查


async def test_create_only_round_trip_except_currency(client, auth):
    await _seed_full_account(client, auth)
    doc_a = (await client.get("/api/backup/export", headers=auth)).json()

    auth_c = await _register(client, "c2_user")
    r = await _post(client, auth_c, doc=doc_a, mode="create_only", dry_run=False)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok", body["errors"]
    assert any("幣別" in w for w in body["warnings"])

    doc_c = (await client.get("/api/backup/export", headers=auth_c)).json()
    norm_a = _norm_export(doc_a)
    norm_c = _norm_export(doc_c)
    # 幣別於 create_only 不還原 → 排除後其餘等價
    assert norm_c["preferences"] == {"currency": "TWD"}
    norm_a["preferences"] = norm_c["preferences"]
    assert norm_c == norm_a


async def test_create_only_reuses_existing_by_name(client, auth):
    doc = {
        "format_version": 4,
        "categories": [{"id": 1, "name": "食物", "parent_id": None}],
        "tags": [{"id": 1, "name": "儲備"}],
        "warehouses": [{"id": 1, "name": "家", "description": "備份描述"}],
        "items": [_item("米", category_id=1, warehouse_id=1, tag_names=["儲備"])],
    }
    auth_c = await _register(client, "c3_user")
    cat = (await client.post("/api/categories", headers=auth_c, json={"name": "食物"})).json()
    # tags 無獨立建立端點 → 以物品標籤建立後沿用既有名稱
    await client.post("/api/items", headers=auth_c, json={"name": "佔位", "tag_names": ["儲備"]})
    tag = (await client.get("/api/tags", headers=auth_c)).json()[0]
    wh = (await client.post("/api/warehouses", headers=auth_c, json={"name": "家"})).json()

    r = await _post(client, auth_c, doc=doc, dry_run=False)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok", body["errors"]
    summary = {e["entity"]: e for e in body["entities"]}
    assert summary["categories"]["reused"] == 1
    # 1 筆標籤列 + 1 筆物品隱式引用 → reused=2
    assert summary["tags"]["reused"] == 2
    assert summary["warehouses"]["reused"] == 1
    assert summary["items"]["created"] == 1

    exported = (await client.get("/api/backup/export", headers=auth_c)).json()
    assert [c["id"] for c in exported["categories"]] == [cat["id"]]
    assert [t["id"] for t in exported["tags"]] == [tag["id"]]
    assert [w["id"] for w in exported["warehouses"]] == [wh["id"]]
    # 既有列不被覆蓋（描述維持空）
    assert exported["warehouses"][0]["description"] is None
    by_name = {i["name"]: i for i in exported["items"]}
    item = by_name["米"]
    assert item["category_id"] == cat["id"]
    assert item["warehouse_id"] == wh["id"]
    assert item["tag_names"] == ["儲備"]


async def test_partial_import_applies_valid_rows(client, auth):
    doc = {
        "format_version": 4,
        "items": [
            _item("好的"),
            {"id": "bad", "name": "  "},
            {"id": "bad2", "name": "其次", "quantity": -1},
        ],
    }
    r = await _post(client, auth, doc=doc, dry_run=False)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "partial"
    assert body["errors_total"] == 2
    assert {e["index"] for e in body["errors"]} == {1, 2}

    exported = (await client.get("/api/backup/export", headers=auth)).json()
    assert [i["name"] for i in exported["items"]] == ["好的"]


async def _backup_import_audits(db_session):
    from sqlalchemy import select as sa_select

    from app.models.favorite_audit_token import AuditLog

    return (
        (
            await db_session.execute(
                sa_select(AuditLog).where(AuditLog.action == "backup.import")
            )
        )
        .scalars()
        .all()
    )


async def test_import_apply_writes_audit_log(client, auth, db_session):
    doc = {"format_version": 4, "items": [_item("稽核")]}
    assert (await _post(client, auth, doc=doc, dry_run=True)).status_code == 200
    assert await _backup_import_audits(db_session) == []  # dry-run 不寫稽核

    assert (await _post(client, auth, doc=doc, dry_run=False)).status_code == 200
    rows = await _backup_import_audits(db_session)
    assert len(rows) == 1
    assert rows[0].resource_type == "backup"
    assert rows[0].resource_id is None
    assert rows[0].meta["mode"] == "create_only"
    assert rows[0].meta["created"]["items"] == 1

    # 再匯入一次 dry-run 不新增
    await _post(client, auth, doc=doc, dry_run=True)
    assert len(await _backup_import_audits(db_session)) == 1


async def test_import_same_name_suffix_and_bad_batch_row(client, auth):
    doc = {
        "format_version": 4,
        "categories": [
            {"id": 1, "name": "食物", "parent_id": None},
            {"id": 2, "name": "食物", "parent_id": None},
        ],
        "items": [_item("甲", category_id=2)],
        "item_batches": [{"item_id": "no-such-item", "quantity": 1}],
    }
    r = await _post(client, auth, doc=doc, dry_run=False)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "partial"
    summary = {e["entity"]: e for e in body["entities"]}
    assert summary["categories"]["created"] == 1
    assert summary["categories"]["renamed"] == 1
    assert summary["item_batches"]["errors"] == 1
    assert body["errors"][0]["entity"] == "item_batches"

    exported = (await client.get("/api/backup/export", headers=auth)).json()
    assert sorted(c["name"] for c in exported["categories"]) == ["食物", "食物 (2)"]
    by_name = {c["name"]: c["id"] for c in exported["categories"]}
    assert exported["items"][0]["category_id"] == by_name["食物 (2)"]
    assert exported["item_batches"] == []


async def test_import_loan_missing_borrower_labeled(client, auth):
    doc = {
        "format_version": 4,
        "items": [_item("借")],
        "loans": [
            {
                "item_id": "11111111-1111-1111-1111-111111111111",
                "borrower_user_id": "99999999-9999-4999-8999-999999999999",
                "borrower_label": None,
                "lent_at": "2026-01-01T00:00:00",
                "expected_return": None,
                "returned_at": None,
                "notes": None,
            }
        ],
    }
    r = await _post(client, auth, doc=doc, dry_run=False)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok", body["errors"]
    assert any("借用人" in w for w in body["warnings"])

    exported = (await client.get("/api/backup/export", headers=auth)).json()
    loan = exported["loans"][0]
    assert loan["borrower_user_id"] is None
    assert loan["borrower_label"] == "（原借用人不存在）"


# ---------------------------------------------------------------------------
# T1.4：replace 清空、隔離性、中止與回滾
# ---------------------------------------------------------------------------


async def _seed_legacy(client, auth) -> None:
    """舊資料：涵蓋會被 replace 清空的各實體。"""
    cat = (await client.post("/api/categories", headers=auth, json={"name": "舊分類"})).json()
    await client.post("/api/locations", headers=auth, json={"name": "舊位置", "kind": "room"})
    await client.post("/api/warehouses", headers=auth, json={"name": "舊倉"})
    await client.post("/api/custom-fields", headers=auth, json={"name": "舊欄位", "field_type": "text"})
    item = (
        await client.post(
            "/api/items", headers=auth, json={"name": "舊物", "quantity": 2, "category_id": cat["id"]}
        )
    ).json()
    await client.post(f"/api/items/{item['id']}/batches", headers=auth, json={"quantity": 1})
    await client.post(
        "/api/lists", headers=auth, json={"kind": "generic", "title": "舊清單"}
    )
    await client.post("/api/stocktakes", headers=auth, json={"name": "舊盤點"})
    await client.post(
        "/api/webhooks",
        headers=auth,
        json={"name": "舊鉤", "url": "https://example.com/old", "events": ["item.created"]},
    )
    await client.put(
        "/api/notifications/preferences",
        headers=auth,
        json={"updates": [{"type": "low_stock", "channel": "email", "enabled": False}]},
    )


async def test_replace_clears_existing_and_imports(client, auth):
    await _seed_legacy(client, auth)
    doc = {
        "format_version": 4,
        "items": [_item("新物", quantity=7)],
        "lists": [{"kind": "generic", "title": "新清單"}],
    }
    r = await _post(client, auth, doc=doc, mode="replace", dry_run=False, confirm="REPLACE")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok", body["errors"]
    assert body["deleted_total"] > 0

    exported = (await client.get("/api/backup/export", headers=auth)).json()
    assert [i["name"] for i in exported["items"]] == ["新物"]
    assert exported["items"][0]["quantity"] == 7
    assert [lst["title"] for lst in exported["lists"]] == ["新清單"]
    # 舊資料全數消失（備份未含者）
    for key in (
        "categories",
        "locations",
        "warehouses",
        "custom_fields",
        "item_batches",
        "stocktakes",
        "webhooks",
        "notification_preferences",
        "loans",
        "quantity_logs",
        "item_versions",
    ):
        assert exported[key] == [], key


async def test_replace_isolation_other_account(client, auth, db_session):
    from sqlalchemy import select as sa_select

    from app.models.group import GroupMember

    auth_b = await _register(client, "iso_b")
    await client.post("/api/items", headers=auth_b, json={"name": "B物", "quantity": 5})
    await client.post("/api/lists", headers=auth_b, json={"kind": "generic", "title": "B清單"})
    await client.post(
        "/api/webhooks",
        headers=auth_b,
        json={"name": "B鉤", "url": "https://example.com/b", "events": ["item.created"]},
    )
    await client.put(
        "/api/notifications/preferences",
        headers=auth_b,
        json={"updates": [{"type": "low_stock", "channel": "email", "enabled": False}]},
    )
    b_group = (await client.post("/api/groups", headers=auth_b, json={"name": "B群"})).json()
    b_before = (await client.get("/api/backup/export", headers=auth_b)).json()

    # A：舊資料 + 群組（B 為成員）
    await _seed_legacy(client, auth)
    a_group = (await client.post("/api/groups", headers=auth, json={"name": "A群"})).json()
    r = await client.post(
        f"/api/groups/{a_group['id']}/members", headers=auth, json={"username": "iso_b"}
    )
    assert r.status_code == 201

    doc = {"format_version": 4, "items": [_item("A新")]}
    r = await _post(client, auth, doc=doc, mode="replace", dry_run=False, confirm="REPLACE")
    assert r.json()["status"] == "ok", r.json()["errors"]

    # B 的資料完全不變
    b_after = (await client.get("/api/backup/export", headers=auth_b)).json()
    assert _norm_export(b_after) == _norm_export(b_before)

    # B 自己建立的群組不受影響（members 亦保留）
    assert [g["name"] for g in b_after["groups_owned"]] == ["B群"]
    rows = (
        await db_session.execute(
            sa_select(GroupMember).where(GroupMember.group_id == b_group["id"])
        )
    ).scalars().all()
    assert len(rows) == 1

    # 「B 對 A 群組」的 membership 屬 A 資料範圍 → 隨 A 群組一併清除
    rows = (
        await db_session.execute(
            sa_select(GroupMember).where(GroupMember.group_id == a_group["id"])
        )
    ).scalars().all()
    assert rows == []


async def test_replace_row_error_aborts_without_writes(client, auth, db_session):
    await client.post("/api/items", headers=auth, json={"name": "原本"})
    doc = {"format_version": 4, "items": [_item("新"), {"id": "bad", "name": "  "}]}
    r = await _post(client, auth, doc=doc, mode="replace", dry_run=False, confirm="REPLACE")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "error"
    assert body["deleted_total"] == 0
    assert body["errors_total"] == 1

    exported = (await client.get("/api/backup/export", headers=auth)).json()
    assert [i["name"] for i in exported["items"]] == ["原本"]
    assert await _backup_import_audits(db_session) == []


async def test_replace_runtime_error_rolls_back(client, auth, monkeypatch):
    import pytest as _pytest
    from app.services import backup_import_service

    await client.post("/api/items", headers=auth, json={"name": "倖存", "quantity": 3})

    async def boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(backup_import_service, "_insert_items", boom)
    doc = {"format_version": 4, "items": [_item("新")]}
    with _pytest.raises(RuntimeError):
        await _post(client, auth, doc=doc, mode="replace", dry_run=False, confirm="REPLACE")

    # 清空＋寫入皆已回滾 → 舊資料完整
    exported = (await client.get("/api/backup/export", headers=auth)).json()
    assert [i["name"] for i in exported["items"]] == ["倖存"]
    assert exported["items"][0]["quantity"] == 3


async def test_replace_dry_run_counts_without_writing(client, auth, db_session):
    await client.post("/api/items", headers=auth, json={"name": "x"})
    await client.post("/api/lists", headers=auth, json={"kind": "generic", "title": "l"})
    doc = {"format_version": 4, "items": [_item("y")]}
    r = await _post(client, auth, doc=doc, mode="replace", dry_run=True)
    assert r.status_code == 200
    body = r.json()
    assert body["deleted_total"] >= 2
    assert body["dry_run"] is True

    exported = (await client.get("/api/backup/export", headers=auth)).json()
    assert [i["name"] for i in exported["items"]] == ["x"]
    assert await _backup_import_audits(db_session) == []
