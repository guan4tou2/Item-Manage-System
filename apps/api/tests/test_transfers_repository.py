from __future__ import annotations
import pytest
from app.auth.password import hash_password
from app.models.item import Item
from app.models.user import User
from app.repositories import transfers_repository as repo


@pytest.fixture
async def two_users_and_item(db_session):
    a = User(email="a@t.io", username="a_user", password_hash=hash_password("secret1234"))
    b = User(email="b@t.io", username="b_user", password_hash=hash_password("secret1234"))
    db_session.add_all([a, b]); await db_session.flush()
    item = Item(owner_id=a.id, name="傘")
    db_session.add(item); await db_session.commit()
    return a, b, item


async def test_create_pending(db_session, two_users_and_item):
    a, b, item = two_users_and_item
    t = await repo.create(db_session, item_id=item.id, from_user_id=a.id, to_user_id=b.id)
    assert t.status == "pending"


async def test_one_pending_per_item(db_session, two_users_and_item):
    a, b, item = two_users_and_item
    await repo.create(db_session, item_id=item.id, from_user_id=a.id, to_user_id=b.id)
    with pytest.raises(Exception):
        await repo.create(db_session, item_id=item.id, from_user_id=a.id, to_user_id=b.id)


async def test_list_for_user(db_session, two_users_and_item):
    a, b, item = two_users_and_item
    await repo.create(db_session, item_id=item.id, from_user_id=a.id, to_user_id=b.id)
    incoming = await repo.list_for_user(db_session, b.id, direction="incoming")
    outgoing = await repo.list_for_user(db_session, a.id, direction="outgoing")
    assert len(incoming) == 1
    assert len(outgoing) == 1


async def test_resolve_accept(db_session, two_users_and_item):
    a, b, item = two_users_and_item
    t = await repo.create(db_session, item_id=item.id, from_user_id=a.id, to_user_id=b.id)
    resolved = await repo.resolve(db_session, t, status="accepted")
    assert resolved.status == "accepted"
    assert resolved.resolved_at is not None


async def test_get_pending_for_item(db_session, two_users_and_item):
    a, b, item = two_users_and_item
    assert await repo.get_pending_for_item(db_session, item.id) is None
    t = await repo.create(db_session, item_id=item.id, from_user_id=a.id, to_user_id=b.id)
    pending = await repo.get_pending_for_item(db_session, item.id)
    assert pending is not None
    assert pending.id == t.id


async def test_get_pending_gone_after_resolve(db_session, two_users_and_item):
    a, b, item = two_users_and_item
    t = await repo.create(db_session, item_id=item.id, from_user_id=a.id, to_user_id=b.id)
    await repo.resolve(db_session, t, status="rejected")
    assert await repo.get_pending_for_item(db_session, item.id) is None
