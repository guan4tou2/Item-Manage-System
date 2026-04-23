from __future__ import annotations

import pytest

from app.auth.password import hash_password
from app.models.notification import Notification
from app.models.user import User
from app.repositories import notifications_repository as repo


@pytest.fixture
async def two_users(db_session):
    a = User(email="a@t.io", username="a_user", password_hash=hash_password("secret1234"))
    b = User(email="b@t.io", username="b_user", password_hash=hash_password("secret1234"))
    db_session.add_all([a, b])
    await db_session.flush()
    return a, b


async def test_create_persists_row(db_session, two_users):
    a, _ = two_users
    n = await repo.create(
        db_session,
        user_id=a.id,
        type="system.welcome",
        title="歡迎",
        body=None,
        link="/dashboard",
    )
    assert n.id is not None
    assert n.read_at is None


async def test_list_paginated_owner_scoped_desc(db_session, two_users):
    a, b = two_users
    await repo.create(db_session, user_id=a.id, type="t", title="A1")
    await repo.create(db_session, user_id=a.id, type="t", title="A2")
    await repo.create(db_session, user_id=b.id, type="t", title="B1")

    rows, total, unread_count = await repo.list_paginated(
        db_session, a.id, unread_only=False, limit=10, offset=0
    )
    assert [r.title for r in rows] == ["A2", "A1"]
    assert total == 2
    assert unread_count == 2


async def test_list_unread_only_filters(db_session, two_users):
    a, _ = two_users
    read_row = await repo.create(db_session, user_id=a.id, type="t", title="read")
    await repo.mark_read(db_session, a.id, read_row.id)
    await repo.create(db_session, user_id=a.id, type="t", title="unread")

    rows, total, unread = await repo.list_paginated(
        db_session, a.id, unread_only=True, limit=10, offset=0
    )
    assert [r.title for r in rows] == ["unread"]
    assert total == 1
    assert unread == 1


async def test_list_pagination(db_session, two_users):
    a, _ = two_users
    for i in range(5):
        await repo.create(db_session, user_id=a.id, type="t", title=f"n{i}")
    page1, total, _ = await repo.list_paginated(db_session, a.id, unread_only=False, limit=2, offset=0)
    page2, _, _ = await repo.list_paginated(db_session, a.id, unread_only=False, limit=2, offset=2)
    assert total == 5
    assert len(page1) == 2
    assert len(page2) == 2
    assert page1[0].title == "n4"
    assert page2[0].title == "n2"


async def test_unread_count(db_session, two_users):
    a, _ = two_users
    r1 = await repo.create(db_session, user_id=a.id, type="t", title="x")
    await repo.create(db_session, user_id=a.id, type="t", title="y")
    await repo.mark_read(db_session, a.id, r1.id)
    assert await repo.unread_count(db_session, a.id) == 1


async def test_mark_read_is_idempotent(db_session, two_users):
    a, _ = two_users
    n = await repo.create(db_session, user_id=a.id, type="t", title="x")
    first = await repo.mark_read(db_session, a.id, n.id)
    original = first.read_at
    second = await repo.mark_read(db_session, a.id, n.id)
    assert second.read_at == original


async def test_mark_read_other_owner_returns_none(db_session, two_users):
    a, b = two_users
    n = await repo.create(db_session, user_id=b.id, type="t", title="x")
    assert await repo.mark_read(db_session, a.id, n.id) is None


async def test_mark_all_read_counts_only_unread(db_session, two_users):
    a, _ = two_users
    r1 = await repo.create(db_session, user_id=a.id, type="t", title="x")
    await repo.mark_read(db_session, a.id, r1.id)
    await repo.create(db_session, user_id=a.id, type="t", title="y")
    await repo.create(db_session, user_id=a.id, type="t", title="z")
    marked = await repo.mark_all_read(db_session, a.id)
    assert marked == 2
    assert await repo.unread_count(db_session, a.id) == 0


async def test_delete_owner_scoped(db_session, two_users):
    a, b = two_users
    n_a = await repo.create(db_session, user_id=a.id, type="t", title="x")
    n_b = await repo.create(db_session, user_id=b.id, type="t", title="y")
    assert await repo.delete(db_session, a.id, n_a.id) is True
    assert await repo.delete(db_session, a.id, n_b.id) is False
    rows, total, _ = await repo.list_paginated(db_session, b.id, unread_only=False, limit=10, offset=0)
    assert total == 1
