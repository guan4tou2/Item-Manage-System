from __future__ import annotations
from datetime import date
from uuid import UUID

from sqlalchemy import delete as sa_delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import _utcnow
from app.models.loan import ItemLoan


async def create(
    session: AsyncSession, *, item_id: UUID,
    borrower_user_id: UUID | None = None,
    borrower_label: str | None = None,
    expected_return: date | None = None,
    notes: str | None = None,
) -> ItemLoan:
    loan = ItemLoan(
        item_id=item_id,
        borrower_user_id=borrower_user_id,
        borrower_label=borrower_label,
        expected_return=expected_return,
        notes=notes,
    )
    session.add(loan)
    await session.commit()
    await session.refresh(loan)
    return loan


async def get(
    session: AsyncSession, item_id: UUID, loan_id: UUID
) -> ItemLoan | None:
    stmt = select(ItemLoan).where(ItemLoan.id == loan_id, ItemLoan.item_id == item_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def get_active(session: AsyncSession, item_id: UUID) -> ItemLoan | None:
    stmt = select(ItemLoan).where(
        ItemLoan.item_id == item_id, ItemLoan.returned_at.is_(None)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_by_item(session: AsyncSession, item_id: UUID) -> list[ItemLoan]:
    stmt = (
        select(ItemLoan)
        .where(ItemLoan.item_id == item_id)
        .order_by(ItemLoan.created_at.desc())
    )
    return list((await session.execute(stmt)).scalars().all())


async def mark_returned(session: AsyncSession, loan: ItemLoan) -> ItemLoan:
    loan.returned_at = _utcnow()
    await session.commit()
    await session.refresh(loan)
    return loan


async def delete(
    session: AsyncSession, item_id: UUID, loan_id: UUID
) -> bool:
    stmt = sa_delete(ItemLoan).where(
        ItemLoan.id == loan_id, ItemLoan.item_id == item_id
    )
    result = await session.execute(stmt)
    await session.commit()
    return (result.rowcount or 0) > 0
