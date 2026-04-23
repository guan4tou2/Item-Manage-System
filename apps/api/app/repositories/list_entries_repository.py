from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import delete as sa_delete
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.list import ListEntry


async def create(
    session: AsyncSession,
    *,
    list_id: UUID,
    name: str,
    position: int | None = None,
    quantity: int | None = None,
    note: str | None = None,
    price: Decimal | None = None,
    link: str | None = None,
    is_done: bool = False,
) -> ListEntry:
    if position is None:
        max_pos = (await session.execute(
            select(func.max(ListEntry.position)).where(ListEntry.list_id == list_id)
        )).scalar_one_or_none()
        position = 0 if max_pos is None else int(max_pos) + 1

    entry = ListEntry(
        list_id=list_id,
        position=position,
        name=name,
        quantity=quantity,
        note=note,
        price=price,
        link=link,
        is_done=is_done,
    )
    session.add(entry)
    await session.commit()
    await session.refresh(entry)
    return entry


async def get(
    session: AsyncSession, list_id: UUID, entry_id: UUID
) -> ListEntry | None:
    stmt = select(ListEntry).where(
        ListEntry.id == entry_id, ListEntry.list_id == list_id
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_all(session: AsyncSession, list_id: UUID) -> list[ListEntry]:
    stmt = (
        select(ListEntry)
        .where(ListEntry.list_id == list_id)
        .order_by(ListEntry.position, ListEntry.created_at)
    )
    return list((await session.execute(stmt)).scalars().all())


async def update(
    session: AsyncSession, entry: ListEntry, fields: dict
) -> ListEntry:
    for k, v in fields.items():
        setattr(entry, k, v)
    await session.commit()
    await session.refresh(entry)
    return entry


async def toggle(session: AsyncSession, entry: ListEntry) -> ListEntry:
    entry.is_done = not entry.is_done
    await session.commit()
    await session.refresh(entry)
    return entry


async def delete(
    session: AsyncSession, list_id: UUID, entry_id: UUID
) -> bool:
    stmt = sa_delete(ListEntry).where(
        ListEntry.id == entry_id, ListEntry.list_id == list_id
    )
    result = await session.execute(stmt)
    await session.commit()
    return (result.rowcount or 0) > 0


async def reorder(
    session: AsyncSession, list_id: UUID, entry_ids: list[UUID]
) -> None:
    current = await list_all(session, list_id)
    current_ids = {e.id for e in current}
    incoming_ids = set(entry_ids)
    if current_ids != incoming_ids:
        raise ValueError("entry_ids must exactly match existing entries for this list")

    by_id = {e.id: e for e in current}
    for idx, eid in enumerate(entry_ids):
        by_id[eid].position = idx
    await session.commit()
