from __future__ import annotations

from app.auth.password import hash_password
from app.models.list import List as ListModel, ListEntry
from app.models.user import User


async def test_list_with_entries_roundtrip(db_session):
    user = User(email="l@t.io", username="l_user", password_hash=hash_password("secret1234"))
    db_session.add(user)
    await db_session.flush()

    lst = ListModel(owner_id=user.id, kind="travel", title="東京五日")
    e1 = ListEntry(name="護照", position=0)
    e2 = ListEntry(name="行動電源", position=1, quantity=2)
    lst.entries = [e1, e2]
    db_session.add(lst)
    await db_session.commit()

    assert lst.id is not None
    assert lst.kind == "travel"
    assert lst.title == "東京五日"
    assert len(lst.entries) == 2
    assert lst.entries[0].name == "護照"
    assert lst.entries[1].quantity == 2
    assert lst.entries[0].is_done is False
