"""Phase 40：稽核覆蓋擴充（登入、物品刪除、權杖、密碼）。

每個案例都直接查 `audit_logs`（另開 session），並在需要時斷言敏感值未落地。
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.favorite_audit_token import AuditLog
from app.models.user import User
from app.services import audit_service

UTC = timezone.utc


async def _register(client, username: str) -> None:
    r = await client.post(
        "/api/auth/register",
        json={"email": f"{username}@t.io", "username": username, "password": "secret1234"},
    )
    assert r.status_code == 201, r.text


async def _login(client, username: str, password: str = "secret1234"):
    return await client.post(
        "/api/auth/login", json={"username": username, "password": password}
    )


async def _auth(client, username: str) -> dict[str, str]:
    await _register(client, username)
    r = await _login(client, username)
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _audit(test_engine, action: str) -> list[AuditLog]:
    maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with maker() as session:
        stmt = (
            select(AuditLog)
            .where(AuditLog.action == action)
            .order_by(AuditLog.created_at.asc())
        )
        return list((await session.execute(stmt)).scalars().all())


async def _user(db_session, username: str) -> User:
    stmt = select(User).where(User.username == username)
    return (await db_session.execute(stmt)).scalar_one()


def _serialized(row: AuditLog) -> str:
    """整列序列化，用來斷言敏感值沒有被寫進稽核。"""
    return " ".join(
        str(part)
        for part in (row.id, row.user_id, row.action, row.resource_type, row.resource_id, row.meta)
    )


# ---------------------------------------------------------------- 登入


async def test_login_success_is_audited(client, test_engine):
    await _register(client, "login_ok")
    user = None
    r = await _login(client, "login_ok")
    assert r.status_code == 200

    rows = [
        row
        for row in await _audit(test_engine, "auth.login")
        if row.meta is None and row.resource_type == "user"
    ]
    # 只會有本測試使用者的登入列（其他測試各自的 DB 是隔離的）
    assert len(rows) == 1
    assert rows[0].resource_id is not None
    assert rows[0].user_id is not None
    assert rows[0].meta is None


async def test_login_failure_is_audited_once_per_window(client, test_engine):
    await _register(client, "bad_pw")
    first = await _login(client, "bad_pw", "wrong-password")
    second = await _login(client, "bad_pw", "wrong-password")
    assert first.status_code == second.status_code == 401

    rows = await _audit(test_engine, "auth.login_failed")
    assert len(rows) == 1
    assert rows[0].resource_type == "user"
    assert rows[0].user_id is not None
    # 不記密碼（不論正確或錯誤）
    assert "wrong-password" not in _serialized(rows[0])


async def test_login_failure_unknown_user_is_not_audited(client, test_engine):
    for _ in range(3):
        r = await _login(client, "nobody_here", "whatever")
        assert r.status_code == 401

    assert await _audit(test_engine, "auth.login_failed") == []


async def test_login_failure_audited_again_after_window(
    client, test_engine, db_session
):
    await _register(client, "window_user")
    user = await _user(db_session, "window_user")
    db_session.add(
        AuditLog(
            user_id=user.id,
            action="auth.login_failed",
            resource_type="user",
            resource_id=str(user.id),
            meta=None,
            created_at=datetime.now(UTC) - timedelta(minutes=11),
        )
    )
    await db_session.commit()

    r = await _login(client, "window_user", "wrong-password")
    assert r.status_code == 401
    assert len(await _audit(test_engine, "auth.login_failed")) == 2


async def test_login_failure_for_inactive_user_is_audited(
    client, test_engine, db_session
):
    await _register(client, "inactive_user")
    user = await _user(db_session, "inactive_user")
    user.is_active = False
    await db_session.commit()

    r = await _login(client, "inactive_user")
    assert r.status_code == 401
    rows = await _audit(test_engine, "auth.login_failed")
    assert len(rows) == 1
    assert str(rows[0].user_id) == str(user.id)


async def test_log_login_failure_swallows_db_errors(monkeypatch, db_session):
    def _boom(*args, **kwargs):
        raise RuntimeError("db down")

    monkeypatch.setattr(audit_service, "select", _boom)
    ok = await audit_service.log_login_failure(
        db_session, user_id=uuid4(), username="someone"
    )
    assert ok is False


# ---------------------------------------------------------------- 物品刪除


async def _item(client, headers, name: str) -> dict:
    r = await client.post("/api/items", headers=headers, json={"name": name})
    assert r.status_code == 201, r.text
    return r.json()


async def test_delete_item_is_audited(client, test_engine):
    headers = await _auth(client, "item_del")
    item = await _item(client, headers, "舊電風扇")

    r = await client.delete(f"/api/items/{item['id']}", headers=headers)
    assert r.status_code == 204

    rows = await _audit(test_engine, "item.deleted")
    assert len(rows) == 1
    assert rows[0].resource_type == "item"
    assert rows[0].resource_id == item["id"]
    assert rows[0].meta == {"name": "舊電風扇"}


async def test_bulk_delete_is_one_summary_row(client, test_engine):
    headers = await _auth(client, "item_bulk")
    items = [await _item(client, headers, f"b{i}") for i in range(3)]

    r = await client.post(
        "/api/items/bulk-delete",
        headers=headers,
        json={"item_ids": [i["id"] for i in items]},
    )
    assert r.status_code == 200

    rows = await _audit(test_engine, "item.bulk_deleted")
    assert len(rows) == 1
    assert rows[0].resource_type == "item"
    assert rows[0].resource_id is None
    assert rows[0].meta["count"] == 3
    assert set(rows[0].meta["item_ids"]) == {i["id"] for i in items}
    assert "names" not in rows[0].meta
    # 不逐筆寫 item.deleted
    assert await _audit(test_engine, "item.deleted") == []


async def test_delete_other_users_item_is_not_audited(client, test_engine):
    headers = await _auth(client, "item_owner_a")
    other_headers = await _auth(client, "item_owner_b")
    item = await _item(client, other_headers, "別人的東西")

    r = await client.delete(f"/api/items/{item['id']}", headers=headers)
    assert r.status_code == 404
    assert await _audit(test_engine, "item.deleted") == []


async def test_audit_failure_does_not_block_item_delete(
    client, test_engine, monkeypatch
):
    headers = await _auth(client, "item_audit_fail")
    item = await _item(client, headers, "照樣刪")

    def _broken_audit(**kwargs):
        raise RuntimeError("audit down")

    monkeypatch.setattr(audit_service, "AuditLog", _broken_audit)
    r = await client.delete(f"/api/items/{item['id']}", headers=headers)
    assert r.status_code == 204
    assert await _audit(test_engine, "item.deleted") == []


# ---------------------------------------------------------------- 權杖


async def test_token_create_and_delete_are_audited_without_secret(
    client, test_engine
):
    headers = await _auth(client, "token_user")

    created = await client.post(
        "/api/users/me/tokens", headers=headers, json={"name": "CI runner"}
    )
    assert created.status_code == 201
    body = created.json()
    raw_token = body["token"]
    token_id = body["id"]

    create_rows = await _audit(test_engine, "token.created")
    assert len(create_rows) == 1
    assert create_rows[0].resource_type == "api_token"
    assert create_rows[0].resource_id == token_id
    assert create_rows[0].meta == {"name": "CI runner"}
    serialized = _serialized(create_rows[0])
    assert raw_token not in serialized
    assert "token_hash" not in serialized
    assert "ims_pat_" not in serialized

    deleted = await client.delete(f"/api/users/me/tokens/{token_id}", headers=headers)
    assert deleted.status_code == 204

    delete_rows = await _audit(test_engine, "token.deleted")
    assert len(delete_rows) == 1
    assert delete_rows[0].resource_id == token_id
    assert delete_rows[0].meta == {"name": "CI runner"}
    assert raw_token not in _serialized(delete_rows[0])


async def test_delete_unknown_token_is_not_audited(client, test_engine):
    headers = await _auth(client, "token_404")
    r = await client.delete(f"/api/users/me/tokens/{uuid4()}", headers=headers)
    assert r.status_code == 404
    assert await _audit(test_engine, "token.deleted") == []


# ---------------------------------------------------------------- 密碼變更


async def test_password_change_is_audited_without_secrets(client, test_engine):
    headers = await _auth(client, "pw_change")

    r = await client.post(
        "/api/users/me/change-password",
        headers=headers,
        json={"current_password": "secret1234", "new_password": "newsecret567"},
    )
    assert r.status_code == 200

    rows = await _audit(test_engine, "user.password_changed")
    assert len(rows) == 1
    assert rows[0].resource_type == "user"
    assert rows[0].meta is None
    serialized = _serialized(rows[0])
    for secret in ("secret1234", "newsecret567", "password_hash", "argon2"):
        assert secret not in serialized


async def test_wrong_current_password_is_not_audited(client, test_engine):
    headers = await _auth(client, "pw_wrong")

    r = await client.post(
        "/api/users/me/change-password",
        headers=headers,
        json={"current_password": "nope", "new_password": "newsecret567"},
    )
    assert r.status_code == 422
    assert await _audit(test_engine, "user.password_changed") == []
