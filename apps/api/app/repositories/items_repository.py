from __future__ import annotations

from collections.abc import Iterable
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.clock import EXPIRING_SOON_DAYS, today_taipei
from app.models.item import Item
from app.models.item_batch import ItemBatch
from app.models.tag import item_tags


def _base_filter_owners(base, owner_ids):
    """Apply an owner filter, accepting either a single UUID or an iterable."""
    if isinstance(owner_ids, (set, frozenset, list, tuple)):
        ids_list = list(owner_ids)
        if not ids_list:
            return base.where(Item.id.is_(None))  # no matches
        return base.where(Item.owner_id.in_(ids_list))
    return base.where(Item.owner_id == owner_ids)


def _base_query(owner_ids):
    base = select(Item).where(Item.is_deleted.is_(False))
    return _base_filter_owners(base, owner_ids)


def _load_options():
    return (
        selectinload(Item.tags),
        selectinload(Item.category),
        selectinload(Item.location),
        selectinload(Item.owner),
    )


async def get_owned(
    session: AsyncSession,
    owner_id: UUID,
    item_id: UUID,
    *,
    for_update: bool = False,
) -> Item | None:
    stmt = (
        _base_query(owner_id)
        .where(Item.id == item_id)
        .options(*_load_options())
    )
    if for_update:
        # PG 才有效：鎖 item 列序列化批次寫入；SQLite 方言會省略，
        # 正確性另由 batches_repository 的條件式 UPDATE 承擔。
        stmt = stmt.with_for_update()
    return (await session.execute(stmt)).scalar_one_or_none()


async def get_visible(
    session: AsyncSession, owner_ids: Iterable[UUID], item_id: UUID
) -> Item | None:
    stmt = (
        _base_query(set(owner_ids))
        .where(Item.id == item_id)
        .options(*_load_options())
    )
    return (await session.execute(stmt)).scalar_one_or_none()


def _soonest_expiry_subquery():
    """每個 item 的最急到期（未耗盡批次）；單一聚合子查詢、走 (item_id,is_depleted) 索引。

    列表聚合走單一 SQL，杜絕對每個 item 逐列查詢（Phase 22 驗收 3）。
    """
    return (
        select(func.min(ItemBatch.expiry_date))
        .where(
            ItemBatch.item_id == Item.id,
            ItemBatch.is_depleted.is_(False),
        )
        .correlate(Item)
        .scalar_subquery()
    )


async def list_by_barcode(
    session: AsyncSession, owner_id: UUID, code: str
) -> list[Item]:
    """內查：owner 範圍、canonical 精確比對（同條碼可多件）。"""
    stmt = (
        _base_query(owner_id)
        .where(Item.barcode == code)
        .order_by(Item.name.asc(), Item.created_at.desc())
        .options(*_load_options())
    )
    return list((await session.execute(stmt)).scalars().all())


async def list_paginated(
    session: AsyncSession,
    owner_ids,
    *,
    q: str | None,
    category_id: int | None,
    location_ids: list[int] | None,
    warehouse_id: int | None = None,
    tag_ids: list[int] | None,
    favorite: bool | None = None,
    expiry: str | None = None,
    sort: str | None = None,
    page: int,
    per_page: int,
) -> tuple[list[tuple[Item, date | None]], int]:
    base = _base_query(owner_ids)
    soonest = _soonest_expiry_subquery()

    if q:
        like = f"%{q}%"
        base = base.where(
            or_(
                Item.name.ilike(like),
                Item.description.ilike(like),
                Item.barcode.ilike(like),
            )
        )
    if category_id is not None:
        base = base.where(Item.category_id == category_id)
    if location_ids is not None:
        # 空集合（例如無子孫的）→ 明確無結果，避免退化成「不篩選」
        base = base.where(Item.location_id.in_(location_ids or [-1]))
    if warehouse_id is not None:
        base = base.where(Item.warehouse_id == warehouse_id)
    if tag_ids:
        base = base.where(
            Item.id.in_(
                select(item_tags.c.item_id).where(item_tags.c.tag_id.in_(tag_ids))
            )
        )
    if favorite is not None:
        base = base.where(Item.is_favorite.is_(favorite))
    if expiry == "expired":
        base = base.where(soonest < today_taipei())
    elif expiry == "expiring_soon":
        today = today_taipei()
        base = base.where(
            soonest.is_not(None),
            soonest >= today,
            soonest <= today + timedelta(days=EXPIRING_SOON_DAYS),
        )

    total_stmt = select(func.count()).select_from(base.subquery())
    total = (await session.execute(total_stmt)).scalar_one()

    stmt = base.add_columns(soonest.label("soonest_expiry"))
    if sort == "expiry_asc":
        stmt = stmt.order_by(
            case((soonest.is_(None), 1), else_=0),
            soonest.asc(),
            Item.created_at.desc(),
        )
    else:
        stmt = stmt.order_by(Item.created_at.desc())
    stmt = (
        stmt.offset((page - 1) * per_page)
        .limit(per_page)
        .options(*_load_options())
    )
    rows = list((await session.execute(stmt)).all())
    return rows, total


async def create(session: AsyncSession, item: Item) -> Item:
    session.add(item)
    await session.commit()
    stmt = select(Item).where(Item.id == item.id).options(*_load_options())
    return (await session.execute(stmt)).scalar_one()


async def save(session: AsyncSession, item: Item) -> Item:
    await session.commit()
    stmt = select(Item).where(Item.id == item.id).options(*_load_options())
    return (await session.execute(stmt)).scalar_one()


async def soft_delete(session: AsyncSession, item: Item) -> None:
    item.is_deleted = True
    await session.commit()
