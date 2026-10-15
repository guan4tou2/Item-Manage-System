from __future__ import annotations

from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import _utcnow
from app.models.item import Item
from app.models.item_batch import ItemBatch


def _expiry_nulls_last():
    return case((ItemBatch.expiry_date.is_(None), 1), else_=0)


def _batch_order():
    return (
        _expiry_nulls_last(),
        ItemBatch.expiry_date.asc(),
        ItemBatch.received_at.asc(),
        ItemBatch.created_at.asc(),
    )


async def list_by_item(session: AsyncSession, item_id: UUID) -> list[ItemBatch]:
    stmt = (
        select(ItemBatch)
        .where(ItemBatch.item_id == item_id)
        .order_by(ItemBatch.is_depleted.asc(), *_batch_order())
    )
    return list((await session.execute(stmt)).scalars().all())


async def list_active(session: AsyncSession, item_id: UUID) -> list[ItemBatch]:
    stmt = (
        select(ItemBatch)
        .where(ItemBatch.item_id == item_id, ItemBatch.is_depleted.is_(False))
        .order_by(*_batch_order())
    )
    return list((await session.execute(stmt)).scalars().all())


async def get(session: AsyncSession, item_id: UUID, batch_id: UUID) -> ItemBatch | None:
    stmt = select(ItemBatch).where(
        ItemBatch.id == batch_id, ItemBatch.item_id == item_id
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def decrement_guarded(
    session: AsyncSession, *, item_id: UUID, batch_id: UUID, quantity: int
) -> bool:
    """原子扣除：僅當批次仍啟用且數量足夠時成功；回傳是否成功。

    這是 SQLite（無 FOR UPDATE）下的正確性保證：條件式 UPDATE 的
    rowcount 檢查讓 stale read 不可能扣出負數。
    """
    batches = ItemBatch.__table__
    stmt = (
        sa.update(batches)
        .where(
            batches.c.id == batch_id,
            batches.c.item_id == item_id,
            batches.c.is_depleted.is_(False),
            batches.c.quantity >= quantity,
        )
        .values(
            quantity=batches.c.quantity - quantity,
            is_depleted=(batches.c.quantity - quantity) <= 0,
            updated_at=_utcnow(),
        )
    )
    result = await session.execute(stmt)
    return (result.rowcount or 0) > 0


async def recalc_item_quantity(session: AsyncSession, item_id: UUID) -> int:
    """以單一 UPDATE 把 items.quantity 重設為「未耗盡批次總和」並回傳新值。"""
    items = Item.__table__
    batches = ItemBatch.__table__
    total = (
        select(sa.func.coalesce(sa.func.sum(batches.c.quantity), 0))
        .where(batches.c.item_id == item_id, batches.c.is_depleted.is_(False))
        .scalar_subquery()
    )
    stmt = (
        sa.update(items)
        .where(items.c.id == item_id)
        .values(quantity=total)
        .returning(items.c.quantity)
    )
    return (await session.execute(stmt)).scalar_one()


async def delete_all_for_item(session: AsyncSession, item_id: UUID) -> None:
    await session.execute(sa.delete(ItemBatch).where(ItemBatch.item_id == item_id))
