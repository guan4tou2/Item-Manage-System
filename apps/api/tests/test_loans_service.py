from __future__ import annotations
import pytest
from fastapi import HTTPException
from app.auth.password import hash_password
from app.models.item import Item
from app.models.user import User
from app.schemas.loan import LoanCreate
from app.services import loans_service as svc


@pytest.fixture
async def owner_and_item(db_session):
    u = User(email="l@t.io", username="l_user", password_hash=hash_password("secret1234"))
    db_session.add(u); await db_session.flush()
    item = Item(owner_id=u.id, name="傘")
    db_session.add(item); await db_session.commit()
    return u, item


async def test_create_with_label(db_session, owner_and_item):
    u, item = owner_and_item
    loan = await svc.create_loan(db_session, u.id, item.id, LoanCreate(borrower_label="張三"))
    assert loan.borrower_label == "張三"


async def test_create_with_username_resolves_user(db_session, owner_and_item):
    u, item = owner_and_item
    friend = User(email="f@t.io", username="friend_user", password_hash=hash_password("secret1234"))
    db_session.add(friend); await db_session.commit()
    loan = await svc.create_loan(db_session, u.id, item.id, LoanCreate(borrower_username="friend_user"))
    assert loan.borrower_user_id == friend.id


async def test_create_unknown_username_422(db_session, owner_and_item):
    u, item = owner_and_item
    with pytest.raises(HTTPException) as ex:
        await svc.create_loan(db_session, u.id, item.id, LoanCreate(borrower_username="ghost"))
    assert ex.value.status_code == 422


async def test_existing_active_rejects(db_session, owner_and_item):
    u, item = owner_and_item
    await svc.create_loan(db_session, u.id, item.id, LoanCreate(borrower_label="a"))
    with pytest.raises(HTTPException) as ex:
        await svc.create_loan(db_session, u.id, item.id, LoanCreate(borrower_label="b"))
    assert ex.value.status_code == 409


async def test_non_owner_cannot_create(db_session, owner_and_item):
    u, item = owner_and_item
    other = User(email="x@t.io", username="x_user", password_hash=hash_password("secret1234"))
    db_session.add(other); await db_session.commit()
    with pytest.raises(HTTPException) as ex:
        await svc.create_loan(db_session, other.id, item.id, LoanCreate(borrower_label="a"))
    assert ex.value.status_code == 404


async def test_return_loan(db_session, owner_and_item):
    u, item = owner_and_item
    loan = await svc.create_loan(db_session, u.id, item.id, LoanCreate(borrower_label="a"))
    returned = await svc.mark_returned(db_session, u.id, item.id, loan.id)
    assert returned.returned_at is not None


async def test_return_already_returned_409(db_session, owner_and_item):
    u, item = owner_and_item
    loan = await svc.create_loan(db_session, u.id, item.id, LoanCreate(borrower_label="a"))
    await svc.mark_returned(db_session, u.id, item.id, loan.id)
    with pytest.raises(HTTPException) as ex:
        await svc.mark_returned(db_session, u.id, item.id, loan.id)
    assert ex.value.status_code == 409
