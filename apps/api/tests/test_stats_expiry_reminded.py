from __future__ import annotations

from datetime import date, timedelta

from app.auth.password import hash_password
from app.clock import today_taipei
from app.models.expiry_alert import ExpiryAlert
from app.models.item import Item
from app.models.item_batch import ItemBatch
from app.models.user import User
from app.services import stats_service


async def _owner(session, name="u1") -> User:
    u = User(
        email=f"{name}@t.io", username=name, password_hash=hash_password("secret1234")
    )
    session.add(u)
    await session.flush()
    return u


async def _expiring_batch(session, owner) -> ItemBatch:
    item = Item(owner_id=owner.id, name="牛奶")
    session.add(item)
    await session.flush()
    batch = ItemBatch(
        item_id=item.id, quantity=1, expiry_date=today_taipei() + timedelta(days=3)
    )
    session.add(batch)
    await session.flush()
    return batch


async def _alert(session, batch, sent_on: date) -> None:
    session.add(ExpiryAlert(batch_id=batch.id, level="d7", sent_on=sent_on))
    await session.flush()


async def test_reminded_today_true(db_session):
    u = await _owner(db_session)
    batch = await _expiring_batch(db_session, u)
    await _alert(db_session, batch, today_taipei())
    await db_session.commit()

    stats = await stats_service.get_expiry(db_session, u.id, days=7)

    assert stats.reminded_today is True


async def test_reminded_today_false_when_only_yesterday(db_session):
    u = await _owner(db_session)
    batch = await _expiring_batch(db_session, u)
    await _alert(db_session, batch, today_taipei() - timedelta(days=1))
    await db_session.commit()

    stats = await stats_service.get_expiry(db_session, u.id, days=7)

    assert stats.reminded_today is False


async def test_reminded_today_ignores_other_owners(db_session):
    mine = await _owner(db_session, "mine")
    other = await _owner(db_session, "other")
    await _expiring_batch(db_session, mine)
    other_batch = await _expiring_batch(db_session, other)
    await _alert(db_session, other_batch, today_taipei())
    await db_session.commit()

    stats = await stats_service.get_expiry(db_session, mine.id, days=7)

    assert stats.reminded_today is False
