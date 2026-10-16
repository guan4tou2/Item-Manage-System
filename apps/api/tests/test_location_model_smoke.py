from __future__ import annotations

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.auth.password import hash_password
from app.models.location import Location
from app.models.user import User


async def _user(session) -> User:
    u = User(
        email="loc@test.io",
        username="loc_user",
        password_hash=hash_password("secret1234"),
    )
    session.add(u)
    await session.flush()
    return u


async def test_location_tree_roundtrip(db_session):
    u = await _user(db_session)
    root = Location(owner_id=u.id, name="1F", kind="floor")
    db_session.add(root)
    await db_session.flush()
    room = Location(owner_id=u.id, parent_id=root.id, name="廚房", kind="room")
    db_session.add(room)
    await db_session.flush()
    shelf = Location(owner_id=u.id, parent_id=room.id, name="上櫃")
    db_session.add(shelf)
    await db_session.commit()

    assert shelf.parent_id == room.id
    assert shelf.kind is None
    assert shelf.sort_order == 0

    loaded = (
        await db_session.execute(
            select(Location).where(Location.id == shelf.id)
        )
    ).scalar_one()
    assert loaded.parent is not None and loaded.parent.name == "廚房"


async def test_sibling_name_must_be_unique(db_session):
    u = await _user(db_session)
    db_session.add(Location(owner_id=u.id, name="1F"))
    await db_session.commit()

    db_session.add(Location(owner_id=u.id, name="1F"))
    with pytest.raises(IntegrityError):
        await db_session.commit()


async def test_child_sibling_name_must_be_unique(db_session):
    u = await _user(db_session)
    root = Location(owner_id=u.id, name="1F")
    db_session.add(root)
    await db_session.flush()
    db_session.add(Location(owner_id=u.id, parent_id=root.id, name="廚房"))
    await db_session.commit()

    db_session.add(Location(owner_id=u.id, parent_id=root.id, name="廚房"))
    with pytest.raises(IntegrityError):
        await db_session.commit()


async def test_same_name_allowed_under_different_parents(db_session):
    u = await _user(db_session)
    first = Location(owner_id=u.id, name="1F")
    second = Location(owner_id=u.id, name="2F")
    db_session.add_all([first, second])
    await db_session.flush()
    db_session.add_all(
        [
            Location(owner_id=u.id, parent_id=first.id, name="廚房"),
            Location(owner_id=u.id, parent_id=second.id, name="廚房"),
        ]
    )
    await db_session.commit()

    rows = (
        await db_session.execute(
            select(Location).where(Location.name == "廚房")
        )
    ).scalars().all()
    assert len(rows) == 2


async def test_delete_parent_with_child_is_blocked_by_fk(db_session):
    u = await _user(db_session)
    root = Location(owner_id=u.id, name="1F")
    db_session.add(root)
    await db_session.flush()
    db_session.add(Location(owner_id=u.id, parent_id=root.id, name="廚房"))
    await db_session.commit()
    root_id = root.id

    # SQLite 預設不啟用 FK；開啟後驗證 DB 層 RESTRICT 定義
    await db_session.execute(text("PRAGMA foreign_keys=ON"))
    await db_session.delete(root)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()

    remaining = (
        await db_session.execute(select(Location).where(Location.id == root_id))
    ).scalar_one_or_none()
    assert remaining is not None
