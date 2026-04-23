from __future__ import annotations
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories import items_repository, loans_repository
from app.schemas.loan import LoanCreate, LoanRead


def _to_read(loan, borrower: User | None) -> LoanRead:
    return LoanRead(
        id=loan.id,
        item_id=loan.item_id,
        borrower_user_id=loan.borrower_user_id,
        borrower_username=borrower.username if borrower else None,
        borrower_label=loan.borrower_label,
        lent_at=loan.lent_at,
        expected_return=loan.expected_return,
        returned_at=loan.returned_at,
        notes=loan.notes,
        created_at=loan.created_at,
        updated_at=loan.updated_at,
    )


async def _ensure_owner(session, user_id, item_id):
    item = await items_repository.get_owned(session, user_id, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="item not found")
    return item


async def list_loans(session, user_id, item_id) -> list[LoanRead]:
    await _ensure_owner(session, user_id, item_id)
    rows = await loans_repository.list_by_item(session, item_id)
    user_ids = [r.borrower_user_id for r in rows if r.borrower_user_id is not None]
    users = {u.id: u for u in (await session.execute(
        select(User).where(User.id.in_(user_ids))
    )).scalars()} if user_ids else {}
    return [_to_read(r, users.get(r.borrower_user_id) if r.borrower_user_id else None) for r in rows]


async def create_loan(
    session: AsyncSession, user_id: UUID, item_id: UUID, body: LoanCreate
) -> LoanRead:
    await _ensure_owner(session, user_id, item_id)
    active = await loans_repository.get_active(session, item_id)
    if active is not None:
        raise HTTPException(status_code=409, detail="item already has an active loan")
    borrower: User | None = None
    borrower_user_id = None
    if body.borrower_username is not None:
        borrower = (await session.execute(
            select(User).where(User.username == body.borrower_username)
        )).scalar_one_or_none()
        if borrower is None:
            raise HTTPException(status_code=422, detail="borrower_username not found")
        borrower_user_id = borrower.id
    loan = await loans_repository.create(
        session,
        item_id=item_id,
        borrower_user_id=borrower_user_id,
        borrower_label=body.borrower_label,
        expected_return=body.expected_return,
        notes=body.notes,
    )
    return _to_read(loan, borrower)


async def mark_returned(
    session: AsyncSession, user_id: UUID, item_id: UUID, loan_id: UUID
) -> LoanRead:
    await _ensure_owner(session, user_id, item_id)
    loan = await loans_repository.get(session, item_id, loan_id)
    if loan is None:
        raise HTTPException(status_code=404, detail="loan not found")
    if loan.returned_at is not None:
        raise HTTPException(status_code=409, detail="already returned")
    returned = await loans_repository.mark_returned(session, loan)
    borrower = None
    if returned.borrower_user_id:
        borrower = (await session.execute(
            select(User).where(User.id == returned.borrower_user_id)
        )).scalar_one_or_none()
    return _to_read(returned, borrower)


async def delete_loan(
    session: AsyncSession, user_id: UUID, item_id: UUID, loan_id: UUID
) -> None:
    await _ensure_owner(session, user_id, item_id)
    if not await loans_repository.delete(session, item_id, loan_id):
        raise HTTPException(status_code=404, detail="loan not found")
