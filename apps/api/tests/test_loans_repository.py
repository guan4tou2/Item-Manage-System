from __future__ import annotations
import pytest
from app.auth.password import hash_password
from app.models.item import Item
from app.models.user import User
from app.repositories import loans_repository as repo


@pytest.fixture
async def owner_and_item(db_session):
    u = User(email="o@t.io", username="o_user", password_hash=hash_password("secret1234"))
    db_session.add(u); await db_session.flush()
    item = Item(owner_id=u.id, name="傘")
    db_session.add(item); await db_session.commit()
    return u, item


async def test_create_loan_with_label(db_session, owner_and_item):
    _, item = owner_and_item
    loan = await repo.create(db_session, item_id=item.id, borrower_label="張三")
    assert loan.returned_at is None
    assert loan.borrower_label == "張三"


async def test_active_loan_uniqueness(db_session, owner_and_item):
    _, item = owner_and_item
    await repo.create(db_session, item_id=item.id, borrower_label="a")
    with pytest.raises(Exception):
        await repo.create(db_session, item_id=item.id, borrower_label="b")


async def test_list_by_item(db_session, owner_and_item):
    _, item = owner_and_item
    a = await repo.create(db_session, item_id=item.id, borrower_label="a")
    await repo.mark_returned(db_session, a)
    await repo.create(db_session, item_id=item.id, borrower_label="b")
    rows = await repo.list_by_item(db_session, item.id)
    assert len(rows) == 2


async def test_get_active(db_session, owner_and_item):
    _, item = owner_and_item
    assert await repo.get_active(db_session, item.id) is None
    loan = await repo.create(db_session, item_id=item.id, borrower_label="a")
    active = await repo.get_active(db_session, item.id)
    assert active is not None
    assert active.id == loan.id


async def test_mark_returned(db_session, owner_and_item):
    _, item = owner_and_item
    loan = await repo.create(db_session, item_id=item.id, borrower_label="a")
    returned = await repo.mark_returned(db_session, loan)
    assert returned.returned_at is not None


async def test_delete(db_session, owner_and_item):
    _, item = owner_and_item
    loan = await repo.create(db_session, item_id=item.id, borrower_label="a")
    ok = await repo.delete(db_session, item.id, loan.id)
    assert ok is True
