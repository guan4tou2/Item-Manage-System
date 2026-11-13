"""Phase 39 T1.2：稽核列表端點（分頁信封、篩選、驗證）。

既有行為（admin-only、停用帳號會寫入稽核）一併保留驗證。
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.auth.password import hash_password
from app.models.user import User

UTC = timezone.utc


async def _register_login(client, username):
    await client.post("/api/auth/register", json={
        "email": f"{username}@t.io", "username": username, "password": "secret1234",
    })
    r = await client.post("/api/auth/login", json={"username": username, "password": "secret1234"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
async def admin_auth(client):
    h = await _register_login(client, "audit_admin")
    r = await client.post("/api/auth/bootstrap-admin", headers=h)
    assert r.status_code == 200
    return h


async def _seed(
    db_session,
    *,
    action: str,
    resource_type: str,
    user_id=None,
    meta=None,
    at=None,
):
    from app.models.favorite_audit_token import AuditLog

    row = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        meta=meta,
        created_at=at or datetime.now(UTC),
    )
    db_session.add(row)
    await db_session.commit()
    return row


async def test_audit_list_requires_admin(client):
    h = await _register_login(client, "regular")
    r = await client.get("/api/admin/audit-logs", headers=h)
    assert r.status_code == 403


async def test_audit_logs_captured_on_deactivate(client, admin_auth):
    await _register_login(client, "victim")
    users = (await client.get("/api/admin/users", headers=admin_auth)).json()
    target = next(u for u in users if u["username"] == "victim")
    await client.patch(f"/api/admin/users/{target['id']}", headers=admin_auth, json={"is_active": False})

    body = (await client.get("/api/admin/audit-logs", headers=admin_auth)).json()
    actions = [r["action"] for r in body["items"]]
    assert "admin.user.set_active" in actions


async def test_audit_list_returns_page_envelope(client, admin_auth):
    body = (await client.get("/api/admin/audit-logs", headers=admin_auth)).json()

    assert set(body) == {"items", "total", "limit", "offset", "facets"}
    assert body["limit"] == 50
    assert body["offset"] == 0
    assert isinstance(body["total"], int)
    assert set(body["facets"]) == {"actions", "resource_types"}
    # 信封的 items 每列都有 user_email 鍵（可為 null）
    for item in body["items"]:
        assert "user_email" in item


async def test_audit_list_filters_and_paginates(client, admin_auth, db_session):
    base = datetime(2026, 10, 1, tzinfo=UTC)
    for i in range(4):
        await _seed(
            db_session,
            action="test.paged",
            resource_type="x",
            at=base + timedelta(minutes=i),
        )
    await _seed(db_session, action="test.other", resource_type="y", at=base)

    first = (
        await client.get(
            "/api/admin/audit-logs?action=test.paged&limit=2&offset=0",
            headers=admin_auth,
        )
    ).json()
    second = (
        await client.get(
            "/api/admin/audit-logs?action=test.paged&limit=2&offset=2",
            headers=admin_auth,
        )
    ).json()

    assert first["total"] == 4
    assert first["limit"] == 2
    assert second["offset"] == 2
    assert len(first["items"]) == 2 and len(second["items"]) == 2
    # 依 created_at DESC
    first_times = [i["created_at"] for i in first["items"]]
    assert first_times == sorted(first_times, reverse=True)
    assert {i["action"] for i in first["items"]} == {"test.paged"}


async def test_audit_list_returns_user_email(client, admin_auth, db_session):
    alice = User(
        email="alice@test.io",
        username="alice_audit",
        password_hash=hash_password("secret1234"),
    )
    db_session.add(alice)
    await db_session.commit()
    await _seed(db_session, action="test.email", resource_type="user", user_id=alice.id)

    body = (
        await client.get("/api/admin/audit-logs?action=test.email", headers=admin_auth)
    ).json()

    assert body["items"][0]["user_email"] == "alice@test.io"


async def test_audit_list_rejects_inverted_date_range(client, admin_auth):
    r = await client.get(
        "/api/admin/audit-logs"
        "?created_from=2026-10-02T00:00:00Z&created_to=2026-10-01T00:00:00Z",
        headers=admin_auth,
    )

    assert r.status_code == 422
    assert r.json()["detail"] == "invalid_date_range"


@pytest.mark.parametrize("query", ["limit=0", "limit=501", "offset=-1"])
async def test_audit_list_rejects_out_of_range_pagination(client, admin_auth, query):
    r = await client.get(f"/api/admin/audit-logs?{query}", headers=admin_auth)

    assert r.status_code == 422


async def test_audit_list_rejects_long_keyword(client, admin_auth):
    r = await client.get(
        f"/api/admin/audit-logs?q={'x' * 201}", headers=admin_auth
    )

    assert r.status_code == 422


async def test_audit_list_facets_cover_all_actions(client, admin_auth, db_session):
    await _seed(db_session, action="test.facet_a", resource_type="x")
    await _seed(db_session, action="test.facet_a", resource_type="x")
    await _seed(db_session, action="test.facet_b", resource_type="y")

    body = (
        await client.get("/api/admin/audit-logs?action=test.facet_a", headers=admin_auth)
    ).json()

    actions = {f["value"]: f["count"] for f in body["facets"]["actions"]}
    # facets 為全域：即使列表已篩選，仍看得到其他動作
    assert actions["test.facet_a"] == 2
    assert actions["test.facet_b"] == 1
