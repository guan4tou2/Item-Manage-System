from __future__ import annotations
import pytest
from fastapi import HTTPException
from app.auth.password import hash_password
from app.models.user import User
from app.schemas.group import GroupAddMember, GroupCreate, GroupUpdate
from app.services import groups_service as svc


@pytest.fixture
async def users(db_session):
    a = User(email="a@t.io", username="a_user", password_hash=hash_password("secret1234"))
    b = User(email="b@t.io", username="b_user", password_hash=hash_password("secret1234"))
    db_session.add_all([a, b]); await db_session.flush()
    return a, b


async def test_create_group_owner_is_member(db_session, users):
    a, _ = users
    summary = await svc.create_group(db_session, a.id, GroupCreate(name="g"))
    detail = await svc.get_group_detail(db_session, a.id, summary.id)
    assert detail.is_owner is True
    assert len(detail.members) == 1


async def test_non_owner_cannot_rename(db_session, users):
    a, b = users
    g = await svc.create_group(db_session, a.id, GroupCreate(name="g"))
    await svc.add_member_by_username(db_session, a.id, g.id, GroupAddMember(username="b_user"))
    with pytest.raises(HTTPException) as ex:
        await svc.update_group(db_session, b.id, g.id, GroupUpdate(name="new"))
    assert ex.value.status_code == 404


async def test_non_owner_cannot_add_member(db_session, users):
    a, b = users
    g = await svc.create_group(db_session, a.id, GroupCreate(name="g"))
    await svc.add_member_by_username(db_session, a.id, g.id, GroupAddMember(username="b_user"))
    with pytest.raises(HTTPException) as ex:
        await svc.add_member_by_username(db_session, b.id, g.id, GroupAddMember(username="a_user"))
    assert ex.value.status_code == 404


async def test_add_member_unknown_username(db_session, users):
    a, _ = users
    g = await svc.create_group(db_session, a.id, GroupCreate(name="g"))
    with pytest.raises(HTTPException) as ex:
        await svc.add_member_by_username(db_session, a.id, g.id, GroupAddMember(username="ghost"))
    assert ex.value.status_code == 404


async def test_add_member_duplicate(db_session, users):
    a, _ = users
    g = await svc.create_group(db_session, a.id, GroupCreate(name="g"))
    with pytest.raises(HTTPException) as ex:
        await svc.add_member_by_username(db_session, a.id, g.id, GroupAddMember(username="a_user"))
    assert ex.value.status_code == 409


async def test_member_can_leave(db_session, users):
    a, b = users
    g = await svc.create_group(db_session, a.id, GroupCreate(name="g"))
    await svc.add_member_by_username(db_session, a.id, g.id, GroupAddMember(username="b_user"))
    await svc.remove_member(db_session, b.id, g.id, b.id)
    detail = await svc.get_group_detail(db_session, a.id, g.id)
    assert len(detail.members) == 1


async def test_cannot_remove_owner(db_session, users):
    a, _ = users
    g = await svc.create_group(db_session, a.id, GroupCreate(name="g"))
    with pytest.raises(HTTPException) as ex:
        await svc.remove_member(db_session, a.id, g.id, a.id)
    assert ex.value.status_code == 409
