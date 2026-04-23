from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.auth.password import hash_password
from app.models.user import User
from app.schemas.list import (
    ListCreate,
    ListEntryCreate,
    ListEntryUpdate,
    ListUpdate,
    ReorderRequest,
)
from app.services import lists_service as svc


@pytest.fixture
async def user(db_session):
    u = User(email="ls@t.io", username="ls_user", password_hash=hash_password("secret1234"))
    db_session.add(u)
    await db_session.flush()
    return u


async def test_create_list_returns_summary(db_session, user):
    body = ListCreate(kind="generic", title="hello")
    summary = await svc.create_list(db_session, user.id, body)
    assert summary.kind == "generic"
    assert summary.entry_count == 0
    assert summary.done_count == 0


async def test_create_list_rejects_date_order(db_session, user):
    body = ListCreate(
        kind="travel", title="T",
        start_date=date(2026, 5, 10), end_date=date(2026, 5, 5),
    )
    with pytest.raises(HTTPException) as ex:
        await svc.create_list(db_session, user.id, body)
    assert ex.value.status_code == 422


async def test_get_list_other_owner_404(db_session, user):
    other = User(email="o@t.io", username="o_user", password_hash=hash_password("secret1234"))
    db_session.add(other)
    await db_session.flush()
    created = await svc.create_list(db_session, other.id, ListCreate(kind="generic", title="x"))
    with pytest.raises(HTTPException) as ex:
        await svc.get_list_detail(db_session, user.id, created.id)
    assert ex.value.status_code == 404


async def test_update_list_missing_404(db_session, user):
    with pytest.raises(HTTPException) as ex:
        await svc.update_list(db_session, user.id, uuid4(), ListUpdate(title="x"))
    assert ex.value.status_code == 404


async def test_create_entry_auto_positions(db_session, user):
    lst = await svc.create_list(db_session, user.id, ListCreate(kind="generic", title="x"))
    a = await svc.create_entry(db_session, user.id, lst.id, ListEntryCreate(name="a"))
    b = await svc.create_entry(db_session, user.id, lst.id, ListEntryCreate(name="b"))
    assert a.position == 0
    assert b.position == 1


async def test_toggle_entry_flips(db_session, user):
    lst = await svc.create_list(db_session, user.id, ListCreate(kind="generic", title="x"))
    e = await svc.create_entry(db_session, user.id, lst.id, ListEntryCreate(name="a"))
    toggled = await svc.toggle_entry(db_session, user.id, lst.id, e.id)
    assert toggled.is_done is True


async def test_update_entry_updates_fields(db_session, user):
    lst = await svc.create_list(db_session, user.id, ListCreate(kind="generic", title="x"))
    e = await svc.create_entry(db_session, user.id, lst.id, ListEntryCreate(name="a"))
    updated = await svc.update_entry(
        db_session, user.id, lst.id, e.id, ListEntryUpdate(name="b")
    )
    assert updated.name == "b"


async def test_delete_entry_other_list_404(db_session, user):
    lst = await svc.create_list(db_session, user.id, ListCreate(kind="generic", title="x"))
    with pytest.raises(HTTPException) as ex:
        await svc.delete_entry(db_session, user.id, lst.id, uuid4())
    assert ex.value.status_code == 404


async def test_reorder_validates_full_set(db_session, user):
    lst = await svc.create_list(db_session, user.id, ListCreate(kind="generic", title="x"))
    a = await svc.create_entry(db_session, user.id, lst.id, ListEntryCreate(name="a"))
    await svc.create_entry(db_session, user.id, lst.id, ListEntryCreate(name="b"))
    with pytest.raises(HTTPException) as ex:
        await svc.reorder_entries(
            db_session, user.id, lst.id, ReorderRequest(entry_ids=[a.id])
        )
    assert ex.value.status_code == 422


async def test_reorder_success(db_session, user):
    lst = await svc.create_list(db_session, user.id, ListCreate(kind="generic", title="x"))
    a = await svc.create_entry(db_session, user.id, lst.id, ListEntryCreate(name="a"))
    b = await svc.create_entry(db_session, user.id, lst.id, ListEntryCreate(name="b"))
    await svc.reorder_entries(
        db_session, user.id, lst.id, ReorderRequest(entry_ids=[b.id, a.id])
    )
    detail = await svc.get_list_detail(db_session, user.id, lst.id)
    assert [e.name for e in detail.entries] == ["b", "a"]
