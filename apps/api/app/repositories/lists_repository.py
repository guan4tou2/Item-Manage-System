from __future__ import annotations

from datetime import date as date_type
from decimal import Decimal
from uuid import UUID

from sqlalchemy import case
from sqlalchemy import delete as sa_delete
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.list import List, ListEntry
from app.schemas.list import ListSummary


async def create(
    session: AsyncSession,
    *,
    owner_id: UUID,
    kind: str,
    title: str,
    description: str | None = None,
    start_date: date_type | None = None,
    end_date: date_type | None = None,
    budget: Decimal | None = None,
) -> List:
    lst = List(
        owner_id=owner_id,
        kind=kind,
        title=title,
        description=description,
        start_date=start_date,
        end_date=end_date,
        budget=budget,
    )
    session.add(lst)
    await session.commit()
    await session.refresh(lst)
    return lst


async def get_owned(
    session: AsyncSession, owner_id: UUID, list_id: UUID
) -> List | None:
    stmt = select(List).where(List.id == list_id, List.owner_id == owner_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_summaries(
    session: AsyncSession,
    owner_id: UUID,
    *,
    kind: str | None,
    limit: int,
    offset: int,
) -> tuple[list[ListSummary], int]:
    entry_count = func.count(ListEntry.id).label("entry_count")
    done_count = func.coalesce(
        func.sum(case((ListEntry.is_done.is_(True), 1), else_=0)),
        0,
    ).label("done_count")

    base = (
        select(List, entry_count, done_count)
        .outerjoin(ListEntry, ListEntry.list_id == List.id)
        .where(List.owner_id == owner_id)
        .group_by(List.id)
        .order_by(List.created_at.desc())
    )
    if kind is not None:
        base = base.where(List.kind == kind)

    count_stmt = select(func.count(List.id)).where(List.owner_id == owner_id)
    if kind is not None:
        count_stmt = count_stmt.where(List.kind == kind)
    total = (await session.execute(count_stmt)).scalar_one()

    stmt = base.limit(limit).offset(offset)
    rows = (await session.execute(stmt)).all()

    summaries = [
        ListSummary(
            id=lst.id,
            kind=lst.kind,
            title=lst.title,
            description=lst.description,
            start_date=lst.start_date,
            end_date=lst.end_date,
            budget=lst.budget,
            entry_count=int(ecount),
            done_count=int(dcount),
            created_at=lst.created_at,
            updated_at=lst.updated_at,
        )
        for lst, ecount, dcount in rows
    ]
    return summaries, int(total)


async def update(
    session: AsyncSession, lst: List, fields: dict
) -> List:
    for k, v in fields.items():
        setattr(lst, k, v)
    await session.commit()
    await session.refresh(lst)
    return lst


async def delete(session: AsyncSession, owner_id: UUID, list_id: UUID) -> bool:
    stmt = sa_delete(List).where(List.id == list_id, List.owner_id == owner_id)
    result = await session.execute(stmt)
    await session.commit()
    return (result.rowcount or 0) > 0
