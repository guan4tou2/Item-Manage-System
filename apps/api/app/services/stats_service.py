from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import locations_repository, preferences_repository, stats_repository
from app.schemas.item import ItemRead
from app.schemas.preferences import currency_from_raw
from app.schemas.stats import (
    ActiveLoan,
    ActivityEntry,
    CategoryBucket,
    CategoryValueBucket,
    ExpiryStats,
    LocationBucket,
    LocationValueBucket,
    LowStockItem,
    OverviewStats,
    TagBucket,
    TrendPoint,
    ValueStats,
    WarehouseBucket,
    WarehouseValueBucket,
)


async def get_overview(session: AsyncSession, owner_id: UUID) -> OverviewStats:
    data = await stats_repository.overview(session, owner_id)
    return OverviewStats(**data)


async def get_by_category(session: AsyncSession, owner_id: UUID) -> list[CategoryBucket]:
    rows = await stats_repository.by_category(session, owner_id)
    return [CategoryBucket(**r) for r in rows]


async def get_by_location(session: AsyncSession, owner_id: UUID) -> list[LocationBucket]:
    rows = await stats_repository.by_location(session, owner_id)
    ids = [r["location_id"] for r in rows if r["location_id"] is not None]
    paths: dict[int, str] = {}
    if ids:
        locations = await locations_repository.fetch_all(session, owner_id)
        paths = locations_repository.paths_for(locations, ids)
    out: list[LocationBucket] = []
    for row in rows:
        location_id = row["location_id"]
        out.append(
            LocationBucket(
                location_id=location_id,
                label=paths.get(location_id) if location_id is not None else None,
                count=row["count"],
            )
        )
    return out


async def get_by_tag(session: AsyncSession, owner_id: UUID, *, limit: int) -> list[TagBucket]:
    rows = await stats_repository.by_tag(session, owner_id, limit=limit)
    return [TagBucket(**r) for r in rows]


async def get_by_warehouse(
    session: AsyncSession, owner_id: UUID
) -> list[WarehouseBucket]:
    rows = await stats_repository.by_warehouse(session, owner_id)
    return [WarehouseBucket(**r) for r in rows]


async def get_recent(session: AsyncSession, owner_id: UUID, *, limit: int) -> list[ItemRead]:
    from app.services.items_service import _to_read
    items = await stats_repository.recent_items(session, owner_id, limit=limit)
    return [_to_read(i) for i in items]


async def get_low_stock(
    session: AsyncSession, owner_id: UUID, *, limit: int
) -> list[LowStockItem]:
    rows = await stats_repository.low_stock(session, owner_id, limit=limit)
    return [LowStockItem(**r) for r in rows]


async def get_expiry(
    session: AsyncSession, owner_id: UUID, *, days: int
) -> ExpiryStats:
    data = await stats_repository.expiry(session, owner_id, days=days)
    return ExpiryStats(**data)


async def get_active_loans(
    session: AsyncSession, owner_id: UUID, *, limit: int
) -> list[ActiveLoan]:
    rows = await stats_repository.active_loans(session, owner_id, limit=limit)
    return [ActiveLoan(**r) for r in rows]


async def get_trend(
    session: AsyncSession, owner_id: UUID, *, days: int
) -> list[TrendPoint]:
    rows = await stats_repository.trend_daily(session, owner_id, days=days)
    return [TrendPoint(**r) for r in rows]


async def get_activity(
    session: AsyncSession, owner_id: UUID, *, limit: int
) -> list[ActivityEntry]:
    rows = await stats_repository.recent_activity(session, owner_id, limit=limit)
    return [ActivityEntry(**r) for r in rows]


def _money(value) -> Decimal:
    """正規化為 2 位小數 Decimal（SQLite REAL／PG numeric 皆適用）。"""
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


async def get_value(session: AsyncSession, owner_id: UUID) -> ValueStats:
    raw_prefs = await preferences_repository.get_raw_preferences(session, owner_id)
    currency = currency_from_raw(raw_prefs)

    totals = await stats_repository.value_totals(session, owner_id)
    cats = await stats_repository.value_by_category(session, owner_id)
    locs = await stats_repository.value_by_location(session, owner_id)
    whs = await stats_repository.value_by_warehouse(session, owner_id)

    ids = [r["location_id"] for r in locs if r["location_id"] is not None]
    paths: dict[int, str] = {}
    if ids:
        locations = await locations_repository.fetch_all(session, owner_id)
        paths = locations_repository.paths_for(locations, ids)

    return ValueStats(
        currency=currency,
        total_value=_money(totals["total_value"]),
        priced_items=totals["priced_items"],
        unpriced_items=totals["unpriced_items"],
        total_items=totals["total_items"],
        by_category=[
            CategoryValueBucket(
                category_id=r["category_id"],
                name=r["name"],
                value=_money(r["value"]),
                count=r["count"],
            )
            for r in cats
        ],
        by_location=[
            LocationValueBucket(
                location_id=r["location_id"],
                label=(
                    paths.get(r["location_id"])
                    if r["location_id"] is not None
                    else None
                ),
                value=_money(r["value"]),
                count=r["count"],
            )
            for r in locs
        ],
        by_warehouse=[
            WarehouseValueBucket(
                warehouse_id=r["warehouse_id"],
                name=r["name"],
                value=_money(r["value"]),
                count=r["count"],
            )
            for r in whs
        ],
    )
