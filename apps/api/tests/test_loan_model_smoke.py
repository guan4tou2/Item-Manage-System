from __future__ import annotations
from datetime import date
from app.auth.password import hash_password
from app.models.item import Item
from app.models.loan import ItemLoan
from app.models.user import User


async def test_loan_with_label(db_session):
    u = User(email="l@t.io", username="l_user", password_hash=hash_password("secret1234"))
    db_session.add(u); await db_session.flush()
    item = Item(owner_id=u.id, name="傘")
    db_session.add(item); await db_session.flush()
    loan = ItemLoan(item_id=item.id, borrower_label="陌生人", expected_return=date(2026, 6, 1))
    db_session.add(loan); await db_session.commit()
    assert loan.id is not None
    assert loan.returned_at is None
