from __future__ import annotations
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
