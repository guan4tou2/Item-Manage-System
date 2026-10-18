from __future__ import annotations

import pytest
from app.auth.password import hash_password
from app.models.group import Group, GroupMember
from app.models.user import User


async def test_group_with_member_roundtrip(db_session):
    owner = User(email="o@t.io", username="o_user", password_hash=hash_password("secret1234"))
    m = User(email="m@t.io", username="m_user", password_hash=hash_password("secret1234"))
    db_session.add_all([owner, m])
    await db_session.flush()
    g = Group(owner_id=owner.id, name="家人")
    g.members = [GroupMember(user_id=owner.id), GroupMember(user_id=m.id)]
    db_session.add(g)
    await db_session.commit()
    assert g.id is not None
    assert len(g.members) == 2


async def test_member_role_defaults_to_editor(db_session):
    owner = User(email="d@t.io", username="d_user", password_hash=hash_password("secret1234"))
    db_session.add(owner)
    await db_session.flush()
    g = Group(owner_id=owner.id, name="家人")
    db_session.add(g)
    await db_session.flush()
    m = GroupMember(group_id=g.id, user_id=owner.id)
    db_session.add(m)
    await db_session.commit()
    assert m.role == "editor"


async def test_member_role_check_rejects_unknown_value(db_session):
    from sqlalchemy.exc import IntegrityError

    owner = User(email="e@t.io", username="e_user", password_hash=hash_password("secret1234"))
    db_session.add(owner)
    await db_session.flush()
    g = Group(owner_id=owner.id, name="家人")
    db_session.add(g)
    await db_session.flush()
    db_session.add(GroupMember(group_id=g.id, user_id=owner.id, role="boss"))
    with pytest.raises(IntegrityError):
        await db_session.commit()
