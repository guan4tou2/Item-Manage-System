"""月報查詢與儲存（Phase 31）。

所有聚合都以「使用者可見 owner 集合」為界（`visibility_service`），
時間區間為 UTC 半開區間 `[start, end)`。
"""
from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.item import Item
from app.models.item_batch import ItemBatch
from app.models.item_history import QuantityLog
from app.models.loan import ItemLoan
from app.models.report import Report


async def create(
    session: AsyncSession,
    *,
    user_id: UUID,
    period: str,
    payload: dict[str, Any],
    generated_at: datetime | None = None,
) -> Report:
    row = Report(user_id=user_id, period=period, payload=payload)
    if generated_at is not None:
        row.generated_at = generated_at
    session.add(row)
    await session.flush()
    return row


async def get_by_user_period(
    session: AsyncSession, user_id: UUID, period: str
) -> Report | None:
    stmt = select(Report).where(
        Report.user_id == user_id, Report.period == period
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def get_owned(
    session: AsyncSession, user_id: UUID, report_id: UUID
) -> Report | None:
    stmt = select(Report).where(
        Report.id == report_id, Report.user_id == user_id
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_for_user(
    session: AsyncSession, user_id: UUID, *, limit: int, offset: int
) -> list[Report]:
    stmt = (
        select(Report)
        .where(Report.user_id == user_id)
        .order_by(Report.period.desc())
        .limit(limit)
        .offset(offset)
    )
    return list((await session.execute(stmt)).scalars().all())


async def count_for_user(session: AsyncSession, user_id: UUID) -> int:
    stmt = select(func.count(Report.id)).where(Report.user_id == user_id)
    return int((await session.execute(stmt)).scalar_one())


# ---------- 聚合 ---------------------------------------------------------


async def totals(
    session: AsyncSession, owner_ids: Sequence[UUID]
) -> tuple[int, int]:
    stmt = select(
        func.count(Item.id),
        func.coalesce(func.sum(Item.quantity), 0),
    ).where(Item.owner_id.in_(owner_ids), Item.is_deleted.is_(False))
    row = (await session.execute(stmt)).one()
    return int(row[0]), int(row[1])


async def has_visible_items(
    session: AsyncSession, owner_ids: Sequence[UUID]
) -> bool:
    stmt = select(func.count(Item.id)).where(
        Item.owner_id.in_(owner_ids), Item.is_deleted.is_(False)
    )
    return int((await session.execute(stmt)).scalar_one()) > 0


async def items_created(
    session: AsyncSession,
    owner_ids: Sequence[UUID],
    *,
    start: datetime,
    end: datetime,
) -> int:
    stmt = select(func.count(Item.id)).where(
        Item.owner_id.in_(owner_ids),
        Item.created_at >= start,
        Item.created_at < end,
    )
    return int((await session.execute(stmt)).scalar_one())


async def items_deleted(
    session: AsyncSession,
    owner_ids: Sequence[UUID],
    *,
    start: datetime,
    end: datetime,
) -> int:
    """軟刪除以 `updated_at` 為刪除時間近似（刪除後不再更新）。"""
    stmt = select(func.count(Item.id)).where(
        Item.owner_id.in_(owner_ids),
        Item.is_deleted.is_(True),
        Item.updated_at >= start,
        Item.updated_at < end,
    )
    return int((await session.execute(stmt)).scalar_one())


async def quantity_deltas(
    session: AsyncSession,
    owner_ids: Sequence[UUID],
    *,
    start: datetime,
    end: datetime,
) -> tuple[int, int]:
    """回傳 (quantity_in, quantity_out)，皆為正數。"""
    delta = QuantityLog.new_quantity - QuantityLog.old_quantity
    stmt = (
        select(
            func.coalesce(func.sum(case((delta > 0, delta), else_=0)), 0),
            func.coalesce(func.sum(case((delta < 0, -delta), else_=0)), 0),
        )
        .select_from(QuantityLog)
        .join(Item, Item.id == QuantityLog.item_id)
        .where(
            Item.owner_id.in_(owner_ids),
            QuantityLog.created_at >= start,
            QuantityLog.created_at < end,
        )
    )
    row = (await session.execute(stmt)).one()
    return int(row[0]), int(row[1])


async def top_categories(
    session: AsyncSession, owner_ids: Sequence[UUID], *, limit: int
) -> list[tuple[str | None, int]]:
    count = func.count(Item.id)
    stmt = (
        select(Item.category_id, Category.name, count)
        .select_from(Item)
        .outerjoin(Category, Category.id == Item.category_id)
        .where(Item.owner_id.in_(owner_ids), Item.is_deleted.is_(False))
        .group_by(Item.category_id, Category.name)
        .order_by(count.desc(), func.coalesce(Item.category_id, 0))
        .limit(limit)
    )
    rows = (await session.execute(stmt)).all()
    return [(row[1], int(row[2])) for row in rows]


async def top_locations(
    session: AsyncSession, owner_ids: Sequence[UUID], *, limit: int
) -> list[tuple[int | None, int]]:
    count = func.count(Item.id)
    stmt = (
        select(Item.location_id, count)
        .where(Item.owner_id.in_(owner_ids), Item.is_deleted.is_(False))
        .group_by(Item.location_id)
        .order_by(count.desc(), func.coalesce(Item.location_id, 0))
        .limit(limit)
    )
    rows = (await session.execute(stmt)).all()
    return [(row[0], int(row[1])) for row in rows]


async def valuation_parts(
    session: AsyncSession,
    owner_ids: Sequence[UUID],
    *,
    start: datetime,
    end: datetime,
) -> tuple[object, object, object, object, int]:
    """回傳 (end, created, deleted, log_delta, unpriced_items)。

    - end：目前存活物品 cost×qty
    - created：期間內建立且目前存活
    - deleted：期間內軟刪除（以 updated_at 近似）
    - log_delta：期間前已存在物品的 quantity_log delta×cost（用於反推月初）
    """
    value = Item.cost * Item.quantity
    priced = (Item.owner_id.in_(owner_ids), Item.cost.is_not(None))

    async def _scalar(stmt) -> object:
        return (await session.execute(stmt)).scalar_one()

    end_stmt = select(func.coalesce(func.sum(value), 0)).where(
        *priced, Item.is_deleted.is_(False)
    )
    created_stmt = select(func.coalesce(func.sum(value), 0)).where(
        *priced,
        Item.is_deleted.is_(False),
        Item.created_at >= start,
        Item.created_at < end,
    )
    deleted_stmt = select(func.coalesce(func.sum(value), 0)).where(
        *priced,
        Item.is_deleted.is_(True),
        # 期間內「建立又刪除」的物品對月初估值淨影響為 0，排除
        Item.created_at < start,
        Item.updated_at >= start,
        Item.updated_at < end,
    )
    log_stmt = (
        select(
            func.coalesce(
                func.sum(
                    (QuantityLog.new_quantity - QuantityLog.old_quantity) * Item.cost
                ),
                0,
            )
        )
        .select_from(QuantityLog)
        .join(Item, Item.id == QuantityLog.item_id)
        .where(
            *priced,
            Item.created_at < start,
            QuantityLog.created_at >= start,
            QuantityLog.created_at < end,
        )
    )
    unpriced_stmt = select(func.count(Item.id)).where(
        Item.owner_id.in_(owner_ids),
        Item.is_deleted.is_(False),
        Item.cost.is_(None),
    )

    return (
        await _scalar(end_stmt),
        await _scalar(created_stmt),
        await _scalar(deleted_stmt),
        await _scalar(log_stmt),
        int(await _scalar(unpriced_stmt)),
    )


async def expiry_counts(
    session: AsyncSession,
    owner_ids: Sequence[UUID],
    *,
    period_end: date,
    horizon_days: int,
) -> tuple[int, int]:
    """回傳 (expiring_soon, expired)：期末未耗盡批次的狀態。"""
    horizon = period_end + timedelta(days=horizon_days)
    base = (
        ItemBatch.quantity > 0,
        ItemBatch.is_depleted.is_(False),
        Item.is_deleted.is_(False),
    )
    expiring = (
        select(func.count(ItemBatch.id))
        .select_from(ItemBatch)
        .join(Item, Item.id == ItemBatch.item_id)
        .where(
            *base,
            Item.owner_id.in_(owner_ids),
            ItemBatch.expiry_date > period_end,
            ItemBatch.expiry_date <= horizon,
        )
    )
    expired = (
        select(func.count(ItemBatch.id))
        .select_from(ItemBatch)
        .join(Item, Item.id == ItemBatch.item_id)
        .where(
            *base,
            Item.owner_id.in_(owner_ids),
            ItemBatch.expiry_date <= period_end,
        )
    )
    return (
        int((await session.execute(expiring)).scalar_one()),
        int((await session.execute(expired)).scalar_one()),
    )


async def loan_counts(
    session: AsyncSession,
    owner_ids: Sequence[UUID],
    *,
    start: datetime,
    end: datetime,
    period_end: date,
) -> tuple[int, int, int]:
    """回傳 (loans_out, loans_returned, loans_overdue)。"""
    out_stmt = (
        select(func.count(ItemLoan.id))
        .select_from(ItemLoan)
        .join(Item, Item.id == ItemLoan.item_id)
        .where(
            Item.owner_id.in_(owner_ids),
            ItemLoan.lent_at >= start,
            ItemLoan.lent_at < end,
        )
    )
    returned_stmt = (
        select(func.count(ItemLoan.id))
        .select_from(ItemLoan)
        .join(Item, Item.id == ItemLoan.item_id)
        .where(
            Item.owner_id.in_(owner_ids),
            ItemLoan.returned_at >= start,
            ItemLoan.returned_at < end,
        )
    )
    overdue_stmt = (
        select(func.count(ItemLoan.id))
        .select_from(ItemLoan)
        .join(Item, Item.id == ItemLoan.item_id)
        .where(
            Item.owner_id.in_(owner_ids),
            ItemLoan.expected_return.is_not(None),
            ItemLoan.expected_return < period_end,
            (ItemLoan.returned_at.is_(None)) | (ItemLoan.returned_at >= end),
        )
    )
    return (
        int((await session.execute(out_stmt)).scalar_one()),
        int((await session.execute(returned_stmt)).scalar_one()),
        int((await session.execute(overdue_stmt)).scalar_one()),
    )
