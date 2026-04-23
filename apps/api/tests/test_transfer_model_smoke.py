from __future__ import annotations
from app.auth.password import hash_password
from app.models.item import Item
from app.models.transfer import ItemTransfer
from app.models.user import User


async def test_transfer_pending(db_session):
    a = User(email="a@t.io", username="a_user", password_hash=hash_password("secret1234"))
    b = User(email="b@t.io", username="b_user", password_hash=hash_password("secret1234"))
    db_session.add_all([a, b]); await db_session.flush()
    item = Item(owner_id=a.id, name="筆")
    db_session.add(item); await db_session.flush()
    t = ItemTransfer(item_id=item.id, from_user_id=a.id, to_user_id=b.id, status="pending")
    db_session.add(t); await db_session.commit()
    assert t.id is not None
    assert t.status == "pending"
