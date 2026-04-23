from __future__ import annotations
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.auth.password import hash_password
from app.models.item import Item
from app.models.user import User


async def test_item_owner_relationship(db_session):
    u = User(email="own@t.io", username="own_user", password_hash=hash_password("secret1234"))
    db_session.add(u); await db_session.flush()
    db_session.add(Item(owner_id=u.id, name="x"))
    await db_session.commit()
    stmt = select(Item).options(selectinload(Item.owner)).where(Item.owner_id == u.id)
    row = (await db_session.execute(stmt)).scalar_one()
    assert row.owner.username == "own_user"
