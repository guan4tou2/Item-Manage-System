from __future__ import annotations
import pytest
from app.auth.password import hash_password
from app.models.user import User
from app.repositories import groups_repository
from app.services.visibility_service import visible_item_owner_ids


@pytest.fixture
async def three_users(db_session):
    a = User(email="a@t.io", username="a_user", password_hash=hash_password("secret1234"))
    b = User(email="b@t.io", username="b_user", password_hash=hash_password("secret1234"))
    c = User(email="c@t.io", username="c_user", password_hash=hash_password("secret1234"))
    db_session.add_all([a, b, c]); await db_session.flush()
    return a, b, c


async def test_alone_returns_self(db_session, three_users):
    a, _, _ = three_users
    assert await visible_item_owner_ids(db_session, a.id) == {a.id}


async def test_group_member_sees_everyone_in_group(db_session, three_users):
    a, b, c = three_users
    g = await groups_repository.create(db_session, owner_id=a.id, name="g")
    await groups_repository.add_member(db_session, g.id, b.id)
    await groups_repository.add_member(db_session, g.id, c.id)
    assert await visible_item_owner_ids(db_session, a.id) == {a.id, b.id, c.id}
    assert await visible_item_owner_ids(db_session, b.id) == {a.id, b.id, c.id}


async def test_non_member_not_visible(db_session, three_users):
    a, b, c = three_users
    g = await groups_repository.create(db_session, owner_id=a.id, name="g")
    await groups_repository.add_member(db_session, g.id, b.id)
    assert c.id not in await visible_item_owner_ids(db_session, a.id)


async def test_union_across_groups(db_session, three_users):
    a, b, c = three_users
    g1 = await groups_repository.create(db_session, owner_id=a.id, name="g1")
    await groups_repository.add_member(db_session, g1.id, b.id)
    g2 = await groups_repository.create(db_session, owner_id=a.id, name="g2")
    await groups_repository.add_member(db_session, g2.id, c.id)
    assert await visible_item_owner_ids(db_session, a.id) == {a.id, b.id, c.id}
