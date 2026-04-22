from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.item import Item
from app.models.location import Location
from app.models.tag import Tag


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
