from __future__ import annotations
import pytest
from fastapi import HTTPException
from app.auth.password import hash_password
from app.models.item import Item
from app.models.user import User
from app.schemas.transfer import TransferCreate
from app.services import transfers_service as svc


@pytest.fixture
async def two_users_and_item(db_session):
    a = User(email="a@t.io", username="a_user", password_hash=hash_password("secret1234"))
    b = User(email="b@t.io", username="b_user", password_hash=hash_password("secret1234"))
    db_session.add_all([a, b]); await db_session.flush()
    item = Item(owner_id=a.id, name="筆")
    db_session.add(item); await db_session.commit()
    return a, b, item


async def test_create_transfer(db_session, two_users_and_item):
    a, b, item = two_users_and_item
    t = await svc.create_transfer(db_session, a.id, TransferCreate(item_id=item.id, to_username="b_user"))
    assert t.status == "pending"
    assert t.to_user_id == b.id


async def test_self_transfer_422(db_session, two_users_and_item):
    a, _, item = two_users_and_item
    with pytest.raises(HTTPException) as ex:
        await svc.create_transfer(db_session, a.id, TransferCreate(item_id=item.id, to_username="a_user"))
    assert ex.value.status_code == 422


async def test_non_owner_404(db_session, two_users_and_item):
    _, b, item = two_users_and_item
    with pytest.raises(HTTPException) as ex:
        await svc.create_transfer(db_session, b.id, TransferCreate(item_id=item.id, to_username="b_user"))
    assert ex.value.status_code == 404


async def test_double_pending_409(db_session, two_users_and_item):
    a, _, item = two_users_and_item
    await svc.create_transfer(db_session, a.id, TransferCreate(item_id=item.id, to_username="b_user"))
    with pytest.raises(HTTPException) as ex:
        await svc.create_transfer(db_session, a.id, TransferCreate(item_id=item.id, to_username="b_user"))
    assert ex.value.status_code == 409


async def test_accept_flips_owner(db_session, two_users_and_item):
    a, b, item = two_users_and_item
    t = await svc.create_transfer(db_session, a.id, TransferCreate(item_id=item.id, to_username="b_user"))
    resolved = await svc.accept_transfer(db_session, b.id, t.id)
    assert resolved.status == "accepted"
    await db_session.refresh(item)
    assert item.owner_id == b.id


async def test_accept_non_recipient_404(db_session, two_users_and_item):
    a, b, item = two_users_and_item
    t = await svc.create_transfer(db_session, a.id, TransferCreate(item_id=item.id, to_username="b_user"))
    with pytest.raises(HTTPException) as ex:
        await svc.accept_transfer(db_session, a.id, t.id)
    assert ex.value.status_code == 404


async def test_cancel_by_sender(db_session, two_users_and_item):
    a, _, item = two_users_and_item
    t = await svc.create_transfer(db_session, a.id, TransferCreate(item_id=item.id, to_username="b_user"))
    resolved = await svc.cancel_transfer(db_session, a.id, t.id)
    assert resolved.status == "cancelled"


async def test_reject_by_recipient(db_session, two_users_and_item):
    a, b, item = two_users_and_item
    t = await svc.create_transfer(db_session, a.id, TransferCreate(item_id=item.id, to_username="b_user"))
    resolved = await svc.reject_transfer(db_session, b.id, t.id)
    assert resolved.status == "rejected"
