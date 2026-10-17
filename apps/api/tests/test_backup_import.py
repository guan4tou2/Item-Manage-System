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
