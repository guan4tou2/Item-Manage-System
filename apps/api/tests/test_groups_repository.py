from __future__ import annotations
import pytest
from app.auth.password import hash_password
from app.models.user import User
from app.repositories import groups_repository as repo


@pytest.fixture
async def users(db_session):
    a = User(email="a@t.io", username="a_user", password_hash=hash_password("secret1234"))
    b = User(email="b@t.io", username="b_user", password_hash=hash_password("secret1234"))
    db_session.add_all([a, b]); await db_session.flush()
    return a, b


async def test_create_adds_owner_as_member(db_session, users):
    a, _ = users
    g = await repo.create(db_session, owner_id=a.id, name="家人")
    members = await repo.list_members(db_session, g.id)
    assert len(members) == 1
    assert members[0].user_id == a.id


async def test_list_for_user_includes_both_owned_and_joined(db_session, users):
    a, b = users
    g1 = await repo.create(db_session, owner_id=a.id, name="a-group")
    g2 = await repo.create(db_session, owner_id=b.id, name="b-group")
    await repo.add_member(db_session, g2.id, a.id)
    rows = await repo.list_for_user(db_session, a.id)
    ids = {r.id for r in rows}
    assert {g1.id, g2.id} == ids


async def test_update_name(db_session, users):
    a, _ = users
    g = await repo.create(db_session, owner_id=a.id, name="old")
    updated = await repo.update(db_session, g, {"name": "new"})
    assert updated.name == "new"


async def test_delete_cascades_members(db_session, users):
    a, _ = users
    g = await repo.create(db_session, owner_id=a.id, name="x")
    ok = await repo.delete(db_session, a.id, g.id)
    assert ok is True


async def test_add_member_unique(db_session, users):
    a, b = users
    g = await repo.create(db_session, owner_id=a.id, name="g")
    await repo.add_member(db_session, g.id, b.id)
    with pytest.raises(Exception):
        await repo.add_member(db_session, g.id, b.id)


async def test_remove_member(db_session, users):
    a, b = users
    g = await repo.create(db_session, owner_id=a.id, name="g")
    await repo.add_member(db_session, g.id, b.id)
    ok = await repo.remove_member(db_session, g.id, b.id)
    assert ok is True
    members = await repo.list_members(db_session, g.id)
    assert {m.user_id for m in members} == {a.id}


async def test_add_member_with_role(db_session, users):
    a, b = users
    g = await repo.create(db_session, owner_id=a.id, name="g")
    m = await repo.add_member(db_session, g.id, b.id, role="viewer")
    assert m.role == "viewer"


async def test_member_roles_for_user(db_session, users):
    a, b = users
    g1 = await repo.create(db_session, owner_id=a.id, name="g1")
    g2 = await repo.create(db_session, owner_id=b.id, name="g2")
    await repo.add_member(db_session, g2.id, a.id, role="viewer")
    roles = await repo.member_roles_for_user(db_session, a.id)
    assert roles == {g1.id: "editor", g2.id: "viewer"}


async def test_member_roles_for_user_empty(db_session, users):
    a, _ = users
    assert await repo.member_roles_for_user(db_session, a.id) == {}
