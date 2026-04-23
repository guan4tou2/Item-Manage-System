from __future__ import annotations
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import _utcnow
from app.models.item import Item
from app.models.stocktake import Stocktake, StocktakeItem
from app.schemas.stocktake import (
    StocktakeCreate,
    StocktakeDetail,
    StocktakeItemRead,
    StocktakeItemScan,
    StocktakeRead,
)
from app.services import item_history_service


async def _summary(session: AsyncSession, st: Stocktake) -> StocktakeRead:
    count_stmt = select(func.count(StocktakeItem.id)).where(StocktakeItem.stocktake_id == st.id)
    disc_stmt = select(func.count(StocktakeItem.id)).where(
        StocktakeItem.stocktake_id == st.id,
        StocktakeItem.expected_quantity != StocktakeItem.actual_quantity,
    )
    item_count = int((await session.execute(count_stmt)).scalar_one())
    disc_count = int((await session.execute(disc_stmt)).scalar_one())
    return StocktakeRead(
        id=st.id, name=st.name, status=st.status,
        started_at=st.started_at, completed_at=st.completed_at,
        item_count=item_count, discrepancy_count=disc_count,
    )


async def list_stocktakes(session: AsyncSession, owner_id: UUID) -> list[StocktakeRead]:
    rows = (await session.execute(
        select(Stocktake).where(Stocktake.owner_id == owner_id).order_by(Stocktake.started_at.desc())
    )).scalars().all()
    return [await _summary(session, r) for r in rows]


async def create_stocktake(
    session: AsyncSession, owner_id: UUID, body: StocktakeCreate
) -> StocktakeRead:
    st = Stocktake(owner_id=owner_id, name=body.name)
    session.add(st)
    await session.commit()
    await session.refresh(st)
    return await _summary(session, st)


async def _ensure_owned(session, owner_id, stocktake_id) -> Stocktake:
    st = await session.get(Stocktake, stocktake_id)
    if st is None or st.owner_id != owner_id:
        raise HTTPException(status_code=404, detail="stocktake not found")
    return st


async def get_stocktake_detail(
    session: AsyncSession, owner_id: UUID, stocktake_id: UUID
) -> StocktakeDetail:
    st = await _ensure_owned(session, owner_id, stocktake_id)
    items = (await session.execute(
        select(StocktakeItem).where(StocktakeItem.stocktake_id == st.id)
        .order_by(StocktakeItem.scanned_at.desc())
    )).scalars().all()
    summary = await _summary(session, st)
    return StocktakeDetail(
        **summary.model_dump(),
        items=[StocktakeItemRead.model_validate(i) for i in items],
    )


async def scan_item(
    session: AsyncSession, owner_id: UUID, stocktake_id: UUID, body: StocktakeItemScan
) -> StocktakeItemRead:
    st = await _ensure_owned(session, owner_id, stocktake_id)
    if st.status != "open":
        raise HTTPException(status_code=409, detail="stocktake is not open")
    # verify item belongs to owner
    item = (await session.execute(
        select(Item).where(
            Item.id == body.item_id,
            Item.owner_id == owner_id,
            Item.is_deleted.is_(False),
        )
    )).scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="item not found")

    # upsert stocktake_item
    existing = (await session.execute(
        select(StocktakeItem).where(
            StocktakeItem.stocktake_id == st.id,
            StocktakeItem.item_id == body.item_id,
        )
    )).scalar_one_or_none()
    if existing:
        existing.actual_quantity = body.actual_quantity
        existing.note = body.note
        existing.scanned_at = _utcnow()
        row = existing
    else:
        row = StocktakeItem(
            stocktake_id=st.id,
            item_id=body.item_id,
            expected_quantity=item.quantity,
            actual_quantity=body.actual_quantity,
            note=body.note,
        )
        session.add(row)
    await session.commit()
    await session.refresh(row)
    return StocktakeItemRead.model_validate(row)


async def complete_stocktake(
    session: AsyncSession, owner_id: UUID, stocktake_id: UUID
) -> StocktakeDetail:
    st = await _ensure_owned(session, owner_id, stocktake_id)
    if st.status != "open":
        raise HTTPException(status_code=409, detail="stocktake already resolved")
    # apply deltas: update each item's quantity to actual, record quantity log
    rows = (await session.execute(
        select(StocktakeItem).where(StocktakeItem.stocktake_id == st.id)
    )).scalars().all()
    for row in rows:
        if row.expected_quantity == row.actual_quantity:
            continue
        item = await session.get(Item, row.item_id)
        if item is None:
            continue
        old_quantity = item.quantity
        item.quantity = row.actual_quantity
        await session.flush()
        await item_history_service.log_quantity_change(
            session,
            item_id=item.id,
            user_id=owner_id,
            old_quantity=old_quantity,
            new_quantity=row.actual_quantity,
            reason=f"stocktake:{st.name}",
        )
    st.status = "completed"
    st.completed_at = _utcnow()
    await session.commit()
    return await get_stocktake_detail(session, owner_id, stocktake_id)


async def cancel_stocktake(
    session: AsyncSession, owner_id: UUID, stocktake_id: UUID
) -> StocktakeRead:
    st = await _ensure_owned(session, owner_id, stocktake_id)
    if st.status != "open":
        raise HTTPException(status_code=409, detail="stocktake already resolved")
    st.status = "cancelled"
    st.completed_at = _utcnow()
    await session.commit()
    await session.refresh(st)
    return await _summary(session, st)
