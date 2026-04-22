from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.item import Item
from app.models.tag import item_tags


def _base_query(owner_id: UUID):
    return select(Item).where(Item.owner_id == owner_id, Item.is_deleted.is_(False))


async def get_owned(session: AsyncSession, owner_id: UUID, item_id: UUID) -> Item | None:
    stmt = (
        _base_query(owner_id)
        .where(Item.id == item_id)
        .options(selectinload(Item.tags), selectinload(Item.category), selectinload(Item.location))
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_paginated(
    session: AsyncSession,
    owner_id: UUID,
    *,
    q: str | None,
    category_id: int | None,
    location_id: int | None,
    tag_ids: list[int] | None,
    page: int,
    per_page: int,
) -> tuple[list[Item], int]:
    base = _base_query(owner_id)

    if q:
        like = f"%{q}%"
        base = base.where(or_(Item.name.ilike(like), Item.description.ilike(like)))
    if category_id is not None:
        base = base.where(Item.category_id == category_id)
    if location_id is not None:
        base = base.where(Item.location_id == location_id)
    if tag_ids:
        base = base.where(
            Item.id.in_(
                select(item_tags.c.item_id).where(item_tags.c.tag_id.in_(tag_ids))
            )
        )

    total_stmt = select(func.count()).select_from(base.subquery())
    total = (await session.execute(total_stmt)).scalar_one()

    stmt = (
        base.order_by(Item.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .options(selectinload(Item.tags), selectinload(Item.category), selectinload(Item.location))
    )
    rows = list((await session.execute(stmt)).scalars().all())
    return rows, total


async def create(session: AsyncSession, item: Item) -> Item:
    session.add(item)
    await session.commit()
    stmt = (
        select(Item)
        .where(Item.id == item.id)
        .options(selectinload(Item.tags), selectinload(Item.category), selectinload(Item.location))
    )
    return (await session.execute(stmt)).scalar_one()


async def save(session: AsyncSession, item: Item) -> Item:
    await session.commit()
    stmt = (
        select(Item)
        .where(Item.id == item.id)
        .options(selectinload(Item.tags), selectinload(Item.category), selectinload(Item.location))
    )
    return (await session.execute(stmt)).scalar_one()


async def soft_delete(session: AsyncSession, item: Item) -> None:
    item.is_deleted = True
    await session.commit()
