from __future__ import annotations

import pytest

from app.auth.password import hash_password
from app.models.user import User
from app.services import notifications_service as svc


@pytest.fixture
async def user(db_session):
    u = User(email="s@t.io", username="s_user", password_hash=hash_password("secret1234"))
    db_session.add(u)
    await db_session.flush()
    return u


async def test_emit_creates_notification(db_session, user):
    n = await svc.emit(
        db_session,
        user_id=user.id,
        type="system.welcome",
        title="歡迎",
        body="開始吧",
        link="/dashboard",
    )
    assert n is not None
    assert n.type == "system.welcome"


async def test_emit_returns_none_on_failure(db_session, user, monkeypatch):
    from app.repositories import notifications_repository as repo

    async def boom(*_args, **_kwargs):
        raise RuntimeError("db blew up")

    monkeypatch.setattr(repo, "create", boom)
    n = await svc.emit(
        db_session,
        user_id=user.id,
        type="low_stock",
        title="x",
    )
    assert n is None


async def test_list_service_delegates(db_session, user):
    await svc.emit(db_session, user_id=user.id, type="t", title="a")
    await svc.emit(db_session, user_id=user.id, type="t", title="b")
    resp = await svc.list_notifications(db_session, user.id, unread_only=False, limit=10, offset=0)
    assert resp.total == 2
    assert resp.unread_count == 2
    assert [n.title for n in resp.items] == ["b", "a"]


async def test_get_unread_count(db_session, user):
    await svc.emit(db_session, user_id=user.id, type="t", title="a")
    await svc.emit(db_session, user_id=user.id, type="t", title="b")
    resp = await svc.get_unread_count(db_session, user.id)
    assert resp.count == 2
