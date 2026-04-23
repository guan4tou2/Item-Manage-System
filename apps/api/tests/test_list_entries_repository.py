from __future__ import annotations

from uuid import uuid4

import pytest

from app.auth.password import hash_password
from app.models.user import User
from app.repositories import lists_repository, list_entries_repository as er


@pytest.fixture
async def owner_and_list(db_session):
    u = User(email="le@t.io", username="le_user", password_hash=hash_password("secret1234"))
    db_session.add(u)
    await db_session.flush()
    lst = await lists_repository.create(
        db_session, owner_id=u.id, kind="generic", title="L"
    )
    return u, lst


async def test_create_entry_auto_position_starts_at_zero(db_session, owner_and_list):
    _, lst = owner_and_list
    e = await er.create(db_session, list_id=lst.id, name="a")
    assert e.position == 0


async def test_create_subsequent_entries_increment_position(db_session, owner_and_list):
    _, lst = owner_and_list
    await er.create(db_session, list_id=lst.id, name="a")
    e2 = await er.create(db_session, list_id=lst.id, name="b")
    assert e2.position == 1


async def test_create_with_explicit_position(db_session, owner_and_list):
    _, lst = owner_and_list
    e = await er.create(db_session, list_id=lst.id, name="a", position=5)
    assert e.position == 5


async def test_get_within_list(db_session, owner_and_list):
    _, lst = owner_and_list
    e = await er.create(db_session, list_id=lst.id, name="a")
    assert (await er.get(db_session, lst.id, e.id)).id == e.id


async def test_get_returns_none_for_other_list(db_session, owner_and_list):
    _, lst = owner_and_list
    e = await er.create(db_session, list_id=lst.id, name="a")
    assert await er.get(db_session, uuid4(), e.id) is None


async def test_update_changes_fields(db_session, owner_and_list):
    _, lst = owner_and_list
    e = await er.create(db_session, list_id=lst.id, name="a")
    updated = await er.update(db_session, e, {"name": "b", "is_done": True})
    assert updated.name == "b"
    assert updated.is_done is True


async def test_toggle_flips_is_done(db_session, owner_and_list):
    _, lst = owner_and_list
    e = await er.create(db_session, list_id=lst.id, name="a")
    toggled = await er.toggle(db_session, e)
    assert toggled.is_done is True
    toggled = await er.toggle(db_session, toggled)
    assert toggled.is_done is False


async def test_delete_removes_entry(db_session, owner_and_list):
    _, lst = owner_and_list
    e = await er.create(db_session, list_id=lst.id, name="a")
    ok = await er.delete(db_session, lst.id, e.id)
    assert ok is True
    assert await er.get(db_session, lst.id, e.id) is None


async def test_delete_returns_false_if_missing(db_session, owner_and_list):
    _, lst = owner_and_list
    ok = await er.delete(db_session, lst.id, uuid4())
    assert ok is False


async def test_list_entries_ordered_by_position(db_session, owner_and_list):
    _, lst = owner_and_list
    a = await er.create(db_session, list_id=lst.id, name="a", position=2)
    b = await er.create(db_session, list_id=lst.id, name="b", position=0)
    c = await er.create(db_session, list_id=lst.id, name="c", position=1)
    rows = await er.list_all(db_session, lst.id)
    assert [r.id for r in rows] == [b.id, c.id, a.id]


async def test_reorder_rewrites_positions_in_order(db_session, owner_and_list):
    _, lst = owner_and_list
    a = await er.create(db_session, list_id=lst.id, name="a")
    b = await er.create(db_session, list_id=lst.id, name="b")
    c = await er.create(db_session, list_id=lst.id, name="c")
    await er.reorder(db_session, lst.id, [c.id, a.id, b.id])
    rows = await er.list_all(db_session, lst.id)
    assert [r.name for r in rows] == ["c", "a", "b"]
    assert [r.position for r in rows] == [0, 1, 2]


async def test_reorder_raises_when_id_set_mismatches(db_session, owner_and_list):
    _, lst = owner_and_list
    a = await er.create(db_session, list_id=lst.id, name="a")
    await er.create(db_session, list_id=lst.id, name="b")
    with pytest.raises(ValueError):
        await er.reorder(db_session, lst.id, [a.id])


async def test_reorder_rejects_foreign_entry_id(db_session, owner_and_list):
    _, lst = owner_and_list
    a = await er.create(db_session, list_id=lst.id, name="a")
    with pytest.raises(ValueError):
        await er.reorder(db_session, lst.id, [a.id, uuid4()])
