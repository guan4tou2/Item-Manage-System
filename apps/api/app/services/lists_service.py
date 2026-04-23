from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import list_entries_repository, lists_repository
from app.schemas.list import (
    ListCreate,
    ListDetail,
    ListEntryCreate,
    ListEntryRead,
    ListEntryUpdate,
    ListListResponse,
    ListSummary,
    ListUpdate,
    ReorderRequest,
)


def _summary_from(lst, entry_count: int, done_count: int) -> ListSummary:
    return ListSummary(
        id=lst.id,
        kind=lst.kind,
        title=lst.title,
        description=lst.description,
        start_date=lst.start_date,
        end_date=lst.end_date,
        budget=lst.budget,
        entry_count=entry_count,
        done_count=done_count,
        created_at=lst.created_at,
        updated_at=lst.updated_at,
    )


def _validate_dates(start, end) -> None:
    if start is not None and end is not None and end < start:
        raise HTTPException(status_code=422, detail="end_date before start_date")


async def _ensure_owned(session, owner_id, list_id):
    lst = await lists_repository.get_owned(session, owner_id, list_id)
    if lst is None:
        raise HTTPException(status_code=404, detail="list not found")
    return lst


async def list_lists(
    session: AsyncSession,
    owner_id: UUID,
    *,
    kind: str | None,
    limit: int,
    offset: int,
) -> ListListResponse:
    items, total = await lists_repository.list_summaries(
        session, owner_id, kind=kind, limit=limit, offset=offset
    )
    return ListListResponse(items=items, total=total)


async def create_list(
    session: AsyncSession, owner_id: UUID, body: ListCreate
) -> ListSummary:
    _validate_dates(body.start_date, body.end_date)
    lst = await lists_repository.create(
        session,
        owner_id=owner_id,
        kind=body.kind,
        title=body.title,
        description=body.description,
        start_date=body.start_date,
        end_date=body.end_date,
        budget=body.budget,
    )
    return _summary_from(lst, 0, 0)


async def get_list_detail(
    session: AsyncSession, owner_id: UUID, list_id: UUID
) -> ListDetail:
    lst = await _ensure_owned(session, owner_id, list_id)
    entries = await list_entries_repository.list_all(session, list_id)
    done_count = sum(1 for e in entries if e.is_done)
    return ListDetail(
        id=lst.id,
        kind=lst.kind,
        title=lst.title,
        description=lst.description,
        start_date=lst.start_date,
        end_date=lst.end_date,
        budget=lst.budget,
        entry_count=len(entries),
        done_count=done_count,
        created_at=lst.created_at,
        updated_at=lst.updated_at,
        entries=[ListEntryRead.model_validate(e) for e in entries],
    )


async def update_list(
    session: AsyncSession, owner_id: UUID, list_id: UUID, body: ListUpdate
) -> ListSummary:
    lst = await _ensure_owned(session, owner_id, list_id)
    fields = body.model_dump(exclude_unset=True)
    new_start = fields.get("start_date", lst.start_date)
    new_end = fields.get("end_date", lst.end_date)
    _validate_dates(new_start, new_end)
    updated = await lists_repository.update(session, lst, fields)
    entries = await list_entries_repository.list_all(session, list_id)
    done_count = sum(1 for e in entries if e.is_done)
    return _summary_from(updated, len(entries), done_count)


async def delete_list(
    session: AsyncSession, owner_id: UUID, list_id: UUID
) -> None:
    if not await lists_repository.delete(session, owner_id, list_id):
        raise HTTPException(status_code=404, detail="list not found")


async def create_entry(
    session: AsyncSession, owner_id: UUID, list_id: UUID, body: ListEntryCreate
) -> ListEntryRead:
    await _ensure_owned(session, owner_id, list_id)
    entry = await list_entries_repository.create(
        session,
        list_id=list_id,
        name=body.name,
        position=body.position,
        quantity=body.quantity,
        note=body.note,
        price=body.price,
        link=body.link,
        is_done=body.is_done,
    )
    return ListEntryRead.model_validate(entry)


async def update_entry(
    session: AsyncSession,
    owner_id: UUID,
    list_id: UUID,
    entry_id: UUID,
    body: ListEntryUpdate,
) -> ListEntryRead:
    await _ensure_owned(session, owner_id, list_id)
    entry = await list_entries_repository.get(session, list_id, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="entry not found")
    fields = body.model_dump(exclude_unset=True)
    updated = await list_entries_repository.update(session, entry, fields)
    return ListEntryRead.model_validate(updated)


async def toggle_entry(
    session: AsyncSession, owner_id: UUID, list_id: UUID, entry_id: UUID
) -> ListEntryRead:
    await _ensure_owned(session, owner_id, list_id)
    entry = await list_entries_repository.get(session, list_id, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="entry not found")
    toggled = await list_entries_repository.toggle(session, entry)
    return ListEntryRead.model_validate(toggled)


async def delete_entry(
    session: AsyncSession, owner_id: UUID, list_id: UUID, entry_id: UUID
) -> None:
    await _ensure_owned(session, owner_id, list_id)
    if not await list_entries_repository.delete(session, list_id, entry_id):
        raise HTTPException(status_code=404, detail="entry not found")


async def reorder_entries(
    session: AsyncSession, owner_id: UUID, list_id: UUID, body: ReorderRequest
) -> None:
    await _ensure_owned(session, owner_id, list_id)
    try:
        await list_entries_repository.reorder(session, list_id, body.entry_ids)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
