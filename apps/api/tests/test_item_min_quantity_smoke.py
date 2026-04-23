from __future__ import annotations

import pytest

from app.auth.password import hash_password
from app.models.item import Item
from app.models.user import User


async def test_item_stores_min_quantity(db_session):
    user = User(email="m@t.io", username="m_user", password_hash=hash_password("secret1234"))
    db_session.add(user)
    await db_session.flush()

    item = Item(owner_id=user.id, name="便當盒", quantity=5, min_quantity=2)
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)
    assert item.min_quantity == 2


async def test_item_min_quantity_defaults_to_none(db_session):
    user = User(email="m2@t.io", username="m2_user", password_hash=hash_password("secret1234"))
    db_session.add(user)
    await db_session.flush()

    item = Item(owner_id=user.id, name="筷子", quantity=1)
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)
    assert item.min_quantity is None
