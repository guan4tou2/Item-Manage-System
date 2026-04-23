from __future__ import annotations

from datetime import date

import pytest

from app.auth.password import hash_password
from app.models.user import User
from app.repositories import lists_repository as repo


@pytest.fixture
async def two_users(db_session):
    a = User(email="a@t.io", username="a_user", password_hash=hash_password("secret1234"))
    b = User(email="b@t.io", username="b_user", password_hash=hash_password("secret1234"))
    db_session.add_all([a, b])
    await db_session.flush()
    return a, b


async def test_create_and_get(db_session, two_users):
    a, _ = two_users
    lst = await repo.create(
        db_session, owner_id=a.id, kind="travel", title="T", description=None,
        start_date=date(2026, 5, 1), end_date=date(2026, 5, 5), budget=None,
    )
    assert lst.id is not None
    fetched = await repo.get_owned(db_session, a.id, lst.id)
    assert fetched is not None
    assert fetched.title == "T"


async def test_get_other_owner_returns_none(db_session, two_users):
    a, b = two_users
    lst = await repo.create(db_session, owner_id=b.id, kind="generic", title="X")
    assert await repo.get_owned(db_session, a.id, lst.id) is None


async def test_list_paginated_with_counts(db_session, two_users):
    a, _ = two_users
    lst = await repo.create(db_session, owner_id=a.id, kind="shopping", title="S")
    from app.models.list import ListEntry
    db_session.add_all([
        ListEntry(list_id=lst.id, position=0, name="x", is_done=False),
        ListEntry(list_id=lst.id, position=1, name="y", is_done=True),
        ListEntry(list_id=lst.id, position=2, name="z", is_done=True),
    ])
    await db_session.commit()

    summaries, total = await repo.list_summaries(
        db_session, a.id, kind=None, limit=10, offset=0
    )
    assert total == 1
    assert len(summaries) == 1
    assert summaries[0].entry_count == 3
    assert summaries[0].done_count == 2


async def test_list_filtered_by_kind(db_session, two_users):
    a, _ = two_users
    await repo.create(db_session, owner_id=a.id, kind="travel", title="T1")
    await repo.create(db_session, owner_id=a.id, kind="shopping", title="S1")
    summaries, total = await repo.list_summaries(
        db_session, a.id, kind="travel", limit=10, offset=0
    )
    assert total == 1
    assert summaries[0].kind == "travel"


async def test_list_owner_scoped(db_session, two_users):
    a, b = two_users
    await repo.create(db_session, owner_id=b.id, kind="generic", title="other")
    summaries, total = await repo.list_summaries(
        db_session, a.id, kind=None, limit=10, offset=0
    )
    assert total == 0


async def test_update_changes_fields(db_session, two_users):
    a, _ = two_users
    lst = await repo.create(db_session, owner_id=a.id, kind="generic", title="before")
    updated = await repo.update(db_session, lst, {"title": "after", "description": "new"})
    assert updated.title == "after"
    assert updated.description == "new"


async def test_delete_cascades_entries(db_session, two_users):
    a, _ = two_users
    lst = await repo.create(db_session, owner_id=a.id, kind="generic", title="X")
    from app.models.list import ListEntry
    db_session.add(ListEntry(list_id=lst.id, position=0, name="e"))
    await db_session.commit()

    ok = await repo.delete(db_session, a.id, lst.id)
    assert ok is True
    assert await repo.get_owned(db_session, a.id, lst.id) is None


async def test_delete_other_owner_returns_false(db_session, two_users):
    a, b = two_users
    lst = await repo.create(db_session, owner_id=b.id, kind="generic", title="X")
    ok = await repo.delete(db_session, a.id, lst.id)
    assert ok is False
