from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.item import Item
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


async def get_owned(session: AsyncSession, owner_id: UUID, item_id: UUID) -> Item | None:
    stmt = (
        _base_query(owner_id)
        .where(Item.id == item_id)
        .options(*_load_options())
    )
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


async def list_paginated(
    session: AsyncSession,
    owner_ids,
    *,
    q: str | None,
    category_id: int | None,
    location_id: int | None,
    tag_ids: list[int] | None,
    page: int,
    per_page: int,
) -> tuple[list[Item], int]:
    base = _base_query(owner_ids)

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
        .options(*_load_options())
    )
    rows = list((await session.execute(stmt)).scalars().all())
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
