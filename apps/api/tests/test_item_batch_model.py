from __future__ import annotations

from datetime import date

from sqlalchemy import select, text

from app.auth.password import hash_password
from app.models.item import Item
from app.models.item_batch import ItemBatch
from app.models.user import User


async def _user(session) -> User:
    u = User(
        email="batch@test.io",
        username="batch_user",
        password_hash=hash_password("secret1234"),
    )
    session.add(u)
    await session.flush()
    return u


async def test_item_batch_roundtrip_defaults(db_session):
    u = await _user(db_session)
    item = Item(owner_id=u.id, name="牛奶")
    db_session.add(item)
    await db_session.flush()

    batch = ItemBatch(
        item_id=item.id,
        quantity=2,
        expiry_date=date(2026, 11, 1),
        received_at=date(2026, 10, 15),
    )
    db_session.add(batch)
    await db_session.commit()

    assert batch.id is not None
    assert batch.is_depleted is False
    assert batch.note is None
    assert batch.created_at is not None
    assert batch.updated_at is not None


async def test_item_track_batches_defaults_false(db_session):
    u = await _user(db_session)
    item = Item(owner_id=u.id, name="米")
    db_session.add(item)
    await db_session.commit()

    assert item.track_batches is False


async def test_batch_without_expiry_allowed(db_session):
    u = await _user(db_session)
    item = Item(owner_id=u.id, name="塩")
    db_session.add(item)
    await db_session.flush()

    batch = ItemBatch(item_id=item.id, quantity=1)
    db_session.add(batch)
    await db_session.commit()

    assert batch.expiry_date is None
    assert batch.received_at is None


async def test_batch_cascade_delete_with_item(db_session):
    u = await _user(db_session)
    item = Item(owner_id=u.id, name="蛋")
    db_session.add(item)
    await db_session.flush()
    batch = ItemBatch(item_id=item.id, quantity=1)
    db_session.add(batch)
    await db_session.commit()
    batch_id = batch.id

    # SQLite 預設不啟用 FK；開啟後驗證 DB 層 CASCADE 定義
    await db_session.execute(text("PRAGMA foreign_keys=ON"))
    await db_session.delete(item)
    await db_session.commit()

    remaining = (
        await db_session.execute(select(ItemBatch).where(ItemBatch.id == batch_id))
    ).scalar_one_or_none()
    assert remaining is None
