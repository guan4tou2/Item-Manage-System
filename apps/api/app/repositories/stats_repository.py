from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, selectinload

from app.models.category import Category
from app.models.item import Item
from app.models.location import Location
from app.models.tag import Tag, item_tags


async def overview(session: AsyncSession, owner_id: UUID) -> dict[str, int]:
    item_stmt = select(
        func.count(Item.id),
        func.coalesce(func.sum(Item.quantity), 0),
    ).where(Item.owner_id == owner_id, Item.is_deleted.is_(False))
    total_items, total_quantity = (await session.execute(item_stmt)).one()

    total_categories = (await session.execute(
        select(func.count(Category.id)).where(Category.owner_id == owner_id)
    )).scalar_one()
    total_locations = (await session.execute(
        select(func.count(Location.id)).where(Location.owner_id == owner_id)
    )).scalar_one()
    total_tags = (await session.execute(
        select(func.count(Tag.id)).where(Tag.owner_id == owner_id)
    )).scalar_one()

    return {
        "total_items": int(total_items),
        "total_quantity": int(total_quantity),
        "total_categories": int(total_categories),
        "total_locations": int(total_locations),
        "total_tags": int(total_tags),
    }


async def by_category(session: AsyncSession, owner_id: UUID) -> list[dict]:
    cat = aliased(Category)
    stmt = (
        select(
            Item.category_id,
            cat.name,
            func.count(Item.id).label("count"),
        )
        .select_from(Item)
        .outerjoin(cat, cat.id == Item.category_id)
        .where(Item.owner_id == owner_id, Item.is_deleted.is_(False))
        .group_by(Item.category_id, cat.name)
        .order_by(func.count(Item.id).desc())
    )
    rows = (await session.execute(stmt)).all()
    return [
        {"category_id": r.category_id, "name": r.name, "count": int(r.count)}
        for r in rows
    ]


async def by_location(session: AsyncSession, owner_id: UUID) -> list[dict]:
    loc = aliased(Location)
    stmt = (
        select(
            Item.location_id,
            loc.floor,
            loc.room,
            loc.zone,
            func.count(Item.id).label("count"),
        )
        .select_from(Item)
        .outerjoin(loc, loc.id == Item.location_id)
        .where(Item.owner_id == owner_id, Item.is_deleted.is_(False))
        .group_by(Item.location_id, loc.floor, loc.room, loc.zone)
        .order_by(func.count(Item.id).desc())
    )
    rows = (await session.execute(stmt)).all()
    out = []
    for r in rows:
        if r.location_id is None:
            label = None
        else:
            parts = [p for p in (r.floor, r.room, r.zone) if p]
            label = " / ".join(parts) if parts else None
        out.append({
            "location_id": r.location_id,
            "label": label,
            "count": int(r.count),
        })
    return out


async def by_tag(session: AsyncSession, owner_id: UUID, *, limit: int) -> list[dict]:
    stmt = (
        select(Tag.id, Tag.name, func.count(item_tags.c.item_id).label("count"))
        .select_from(Tag)
        .join(item_tags, item_tags.c.tag_id == Tag.id)
        .join(Item, Item.id == item_tags.c.item_id)
        .where(
            Tag.owner_id == owner_id,
            Item.owner_id == owner_id,
            Item.is_deleted.is_(False),
        )
        .group_by(Tag.id, Tag.name)
        .order_by(func.count(item_tags.c.item_id).desc())
        .limit(limit)
    )
    rows = (await session.execute(stmt)).all()
    return [
        {"tag_id": r.id, "name": r.name, "count": int(r.count)}
        for r in rows
    ]


async def recent_items(session: AsyncSession, owner_id: UUID, *, limit: int) -> list[Item]:
    stmt = (
        select(Item)
        .where(Item.owner_id == owner_id, Item.is_deleted.is_(False))
        .order_by(Item.created_at.desc())
        .limit(limit)
        .options(
            selectinload(Item.tags),
            selectinload(Item.category),
            selectinload(Item.location),
        )
    )
    return list((await session.execute(stmt)).scalars().all())
