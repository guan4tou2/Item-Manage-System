"""Phase 39 T1.3：稽核 CSV 匯出端點。"""
from __future__ import annotations

import csv
import io
import json
import re
from datetime import datetime, timezone

import pytest

from app.models.favorite_audit_token import AuditLog

UTC = timezone.utc


async def _register_login(client, username):
    await client.post("/api/auth/register", json={
        "email": f"{username}@t.io", "username": username, "password": "secret1234",
    })
    r = await client.post("/api/auth/login", json={"username": username, "password": "secret1234"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
async def admin_auth(client):
    h = await _register_login(client, "export_admin")
    r = await client.post("/api/auth/bootstrap-admin", headers=h)
    assert r.status_code == 200
    return h


def _rows(text: str) -> list[list[str]]:
    return list(csv.reader(io.StringIO(text.lstrip("\ufeff"))))


async def _seed(db_session, *, action: str, resource_type: str, resource_id=None, meta=None, at=None):
    row = AuditLog(
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        meta=meta,
        created_at=at or datetime(2026, 10, 1, 12, 0, tzinfo=UTC),
    )
    db_session.add(row)
    await db_session.commit()
    return row


async def test_export_requires_admin(client):
    h = await _register_login(client, "export_regular")
    r = await client.get("/api/admin/audit-logs/export.csv", headers=h)
    assert r.status_code == 403


async def test_export_returns_utf8_bom_csv_with_header(client, admin_auth, db_session):
    await _seed(db_session, action="test.csv", resource_type="x", resource_id="r-1")

    r = await client.get("/api/admin/audit-logs/export.csv", headers=admin_auth)

    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert r.text.startswith("\ufeff")
    assert re.search(
        r'attachment; filename="audit-logs-\d{8}\.csv"', r.headers["content-disposition"]
    )
    header = _rows(r.text)[0]
    assert header == [
        "created_at",
        "user_email",
        "user_id",
        "action",
        "resource_type",
        "resource_id",
        "meta",
    ]


async def test_export_row_values_and_iso_timestamp(client, admin_auth, db_session):
    await _seed(
        db_session,
        action="test.values",
        resource_type="item",
        resource_id="item-9",
        meta={"name": "牛奶"},
    )

    rows = _rows((await client.get("/api/admin/audit-logs/export.csv", headers=admin_auth)).text)
    row = next(r for r in rows[1:] if r[3] == "test.values")

    assert row[0].startswith("2026-10-01T12:00:00")
    assert row[0].endswith("Z")
    assert row[1] == ""  # 無 user → user_email 空字串
    assert row[4] == "item"
    assert row[5] == "item-9"
    assert json.loads(row[6]) == {"name": "牛奶"}


async def test_export_escapes_commas_quotes_and_newlines(client, admin_auth, db_session):
    tricky = {"note": 'a,b "c"\n第二行'}
    await _seed(db_session, action="test.tricky", resource_type="x", meta=tricky)

    text = (await client.get("/api/admin/audit-logs/export.csv", headers=admin_auth)).text
    row = next(r for r in _rows(text)[1:] if r[3] == "test.tricky")

    # csv 模組 round-trip：meta 欄位原樣還原
    assert json.loads(row[6]) == tricky


async def test_export_applies_filters(client, admin_auth, db_session):
    await _seed(db_session, action="test.keep", resource_type="x")
    await _seed(db_session, action="test.drop", resource_type="y")

    text = (
        await client.get(
            "/api/admin/audit-logs/export.csv?action=test.keep", headers=admin_auth
        )
    ).text

    actions = [r[3] for r in _rows(text)[1:]]
    assert actions == ["test.keep"]


async def test_export_rejects_inverted_date_range(client, admin_auth):
    r = await client.get(
        "/api/admin/audit-logs/export.csv"
        "?created_from=2026-10-02T00:00:00Z&created_to=2026-10-01T00:00:00Z",
        headers=admin_auth,
    )

    assert r.status_code == 422
    assert r.json()["detail"] == "invalid_date_range"


async def test_export_truncates_at_max_rows(client, admin_auth, db_session, monkeypatch):
    from app.services import audit_service

    for i in range(5):
        await _seed(db_session, action=f"test.trunc.{i}", resource_type="x")
    monkeypatch.setattr(audit_service, "DEFAULT_EXPORT_MAX_ROWS", 2)

    text = (await client.get("/api/admin/audit-logs/export.csv", headers=admin_auth)).text

    assert len(_rows(text)) == 3  # 表頭 + 2 列
