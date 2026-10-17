from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.auth.password import hash_password
from app.models.item import Item
from app.models.user import User


async def test_item_stores_cost(db_session):
    user = User(email="c@t.io", username="c_user", password_hash=hash_password("secret1234"))
    db_session.add(user)
    await db_session.flush()

    item = Item(owner_id=user.id, name="咖啡豆", quantity=2, cost=Decimal("12.34"))
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)
    assert item.cost == Decimal("12.34")


async def test_item_cost_defaults_to_none(db_session):
    user = User(email="c2@t.io", username="c2_user", password_hash=hash_password("secret1234"))
    db_session.add(user)
    await db_session.flush()

    item = Item(owner_id=user.id, name="濾紙", quantity=1)
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)
    assert item.cost is None


async def test_item_cost_rejects_negative(db_session):
    user = User(email="c3@t.io", username="c3_user", password_hash=hash_password("secret1234"))
    db_session.add(user)
    await db_session.flush()

    item = Item(owner_id=user.id, name="負值成本", quantity=1, cost=Decimal("-0.01"))
    db_session.add(item)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()
