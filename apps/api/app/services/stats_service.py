from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import stats_repository
from app.schemas.item import ItemRead
from app.schemas.stats import (
    CategoryBucket,
    LocationBucket,
    OverviewStats,
    TagBucket,
)


async def get_overview(session: AsyncSession, owner_id: UUID) -> OverviewStats:
    data = await stats_repository.overview(session, owner_id)
    return OverviewStats(**data)


async def get_by_category(session: AsyncSession, owner_id: UUID) -> list[CategoryBucket]:
    rows = await stats_repository.by_category(session, owner_id)
    return [CategoryBucket(**r) for r in rows]


async def get_by_location(session: AsyncSession, owner_id: UUID) -> list[LocationBucket]:
    rows = await stats_repository.by_location(session, owner_id)
    return [LocationBucket(**r) for r in rows]


async def get_by_tag(session: AsyncSession, owner_id: UUID, *, limit: int) -> list[TagBucket]:
    rows = await stats_repository.by_tag(session, owner_id, limit=limit)
    return [TagBucket(**r) for r in rows]


async def get_recent(session: AsyncSession, owner_id: UUID, *, limit: int) -> list[ItemRead]:
    from app.services.items_service import _to_read
    items = await stats_repository.recent_items(session, owner_id, limit=limit)
    return [_to_read(i) for i in items]
