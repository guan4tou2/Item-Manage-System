from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, selectinload

from app.models.category import Category
from app.models.item import Item
from app.models.item_history import ItemVersion, QuantityLog
from app.models.loan import ItemLoan
from app.models.location import Location
from app.models.tag import Tag, item_tags
from app.models.warehouse import Warehouse


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
    total_warehouses = (await session.execute(
        select(func.count(Warehouse.id)).where(Warehouse.owner_id == owner_id)
    )).scalar_one()

    low_stock_items = (await session.execute(
        select(func.count(Item.id)).where(
            Item.owner_id == owner_id,
            Item.is_deleted.is_(False),
            Item.min_quantity.is_not(None),
            Item.quantity < Item.min_quantity,
        )
    )).scalar_one()

    active_loans = (await session.execute(
        select(func.count(ItemLoan.id))
        .select_from(ItemLoan)
        .join(Item, Item.id == ItemLoan.item_id)
        .where(
            Item.owner_id == owner_id,
            Item.is_deleted.is_(False),
            ItemLoan.returned_at.is_(None),
        )
    )).scalar_one()

    return {
        "total_items": int(total_items),
        "total_quantity": int(total_quantity),
        "total_categories": int(total_categories),
        "total_locations": int(total_locations),
        "total_tags": int(total_tags),
        "total_warehouses": int(total_warehouses),
        "low_stock_items": int(low_stock_items),
        "active_loans": int(active_loans),
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
            selectinload(Item.owner),
        )
    )
    return list((await session.execute(stmt)).scalars().all())


async def by_warehouse(session: AsyncSession, owner_id: UUID) -> list[dict]:
    wh = aliased(Warehouse)
    stmt = (
        select(
            Item.warehouse_id,
            wh.name,
            func.count(Item.id).label("count"),
        )
        .select_from(Item)
        .outerjoin(wh, wh.id == Item.warehouse_id)
        .where(Item.owner_id == owner_id, Item.is_deleted.is_(False))
        .group_by(Item.warehouse_id, wh.name)
        .order_by(func.count(Item.id).desc())
    )
    rows = (await session.execute(stmt)).all()
    return [
        {
            "warehouse_id": r.warehouse_id,
            "name": r.name,
            "count": int(r.count),
        }
        for r in rows
    ]


async def low_stock(
    session: AsyncSession, owner_id: UUID, *, limit: int
) -> list[dict]:
    stmt = (
        select(
            Item.id,
            Item.name,
            Item.quantity,
            Item.min_quantity,
        )
        .where(
            Item.owner_id == owner_id,
            Item.is_deleted.is_(False),
            Item.min_quantity.is_not(None),
            Item.quantity < Item.min_quantity,
        )
        .order_by((Item.min_quantity - Item.quantity).desc(), Item.name)
        .limit(limit)
    )
    rows = (await session.execute(stmt)).all()
    return [
        {
            "item_id": r.id,
            "name": r.name,
            "quantity": int(r.quantity),
            "min_quantity": int(r.min_quantity),
            "deficit": int(r.min_quantity) - int(r.quantity),
        }
        for r in rows
    ]


async def active_loans(
    session: AsyncSession, owner_id: UUID, *, limit: int
) -> list[dict]:
    today = date.today()
    stmt = (
        select(
            ItemLoan.id,
            ItemLoan.item_id,
            Item.name,
            ItemLoan.borrower_label,
            ItemLoan.lent_at,
            ItemLoan.expected_return,
        )
        .select_from(ItemLoan)
        .join(Item, Item.id == ItemLoan.item_id)
        .where(
            Item.owner_id == owner_id,
            Item.is_deleted.is_(False),
            ItemLoan.returned_at.is_(None),
        )
        .order_by(
            ItemLoan.expected_return.is_(None),  # non-null first
            ItemLoan.expected_return.asc(),
            ItemLoan.lent_at.asc(),
        )
        .limit(limit)
    )
    rows = (await session.execute(stmt)).all()
    out = []
    for r in rows:
        overdue = bool(r.expected_return and r.expected_return < today)
        out.append({
            "loan_id": r.id,
            "item_id": r.item_id,
            "item_name": r.name,
            "borrower_label": r.borrower_label,
            "lent_at": r.lent_at,
            "expected_return": r.expected_return,
            "is_overdue": overdue,
        })
    return out


async def trend_daily(
    session: AsyncSession, owner_id: UUID, *, days: int
) -> list[dict]:
    """Count items created per day over the last `days` days (inclusive today).

    Returns a dense series: every day gets an entry even if count is 0.
    """
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=days - 1)
    start_dt = datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc)

    stmt = (
        select(
            func.date(Item.created_at).label("day"),
            func.count(Item.id).label("count"),
        )
        .where(
            Item.owner_id == owner_id,
            Item.is_deleted.is_(False),
            Item.created_at >= start_dt,
        )
        .group_by(func.date(Item.created_at))
    )
    rows = (await session.execute(stmt)).all()
    counts: dict[date, int] = {}
    for r in rows:
        day_val = r.day
        if isinstance(day_val, str):
            day_val = date.fromisoformat(day_val)
        elif isinstance(day_val, datetime):
            day_val = day_val.date()
        counts[day_val] = int(r.count)

    out: list[dict] = []
    for i in range(days):
        d = start + timedelta(days=i)
        out.append({"day": d, "count": counts.get(d, 0)})
    return out


async def recent_activity(
    session: AsyncSession, owner_id: UUID, *, limit: int
) -> list[dict]:
    """Merge quantity logs + loan events + item version snapshots into one feed."""
    entries: list[dict] = []

    qstmt = (
        select(
            QuantityLog.created_at,
            QuantityLog.item_id,
            Item.name,
            QuantityLog.old_quantity,
            QuantityLog.new_quantity,
            QuantityLog.reason,
        )
        .select_from(QuantityLog)
        .join(Item, Item.id == QuantityLog.item_id)
        .where(Item.owner_id == owner_id, Item.is_deleted.is_(False))
        .order_by(QuantityLog.created_at.desc())
        .limit(limit)
    )
    for r in (await session.execute(qstmt)).all():
        delta = r.new_quantity - r.old_quantity
        sign = "+" if delta > 0 else ""
        reason_suffix = f" ({r.reason})" if r.reason else ""
        entries.append({
            "kind": "quantity",
            "at": r.created_at,
            "item_id": r.item_id,
            "item_name": r.name,
            "summary": f"{r.name} {sign}{delta}{reason_suffix}",
        })

    lstmt_out = (
        select(
            ItemLoan.lent_at,
            ItemLoan.item_id,
            Item.name,
            ItemLoan.borrower_label,
        )
        .select_from(ItemLoan)
        .join(Item, Item.id == ItemLoan.item_id)
        .where(Item.owner_id == owner_id, Item.is_deleted.is_(False))
        .order_by(ItemLoan.lent_at.desc())
        .limit(limit)
    )
    for r in (await session.execute(lstmt_out)).all():
        who = r.borrower_label or "someone"
        entries.append({
            "kind": "loan_out",
            "at": r.lent_at,
            "item_id": r.item_id,
            "item_name": r.name,
            "summary": f"lent {r.name} to {who}",
        })

    lstmt_back = (
        select(
            ItemLoan.returned_at,
            ItemLoan.item_id,
            Item.name,
        )
        .select_from(ItemLoan)
        .join(Item, Item.id == ItemLoan.item_id)
        .where(
            Item.owner_id == owner_id,
            Item.is_deleted.is_(False),
            ItemLoan.returned_at.is_not(None),
        )
        .order_by(ItemLoan.returned_at.desc())
        .limit(limit)
    )
    for r in (await session.execute(lstmt_back)).all():
        entries.append({
            "kind": "loan_return",
            "at": r.returned_at,
            "item_id": r.item_id,
            "item_name": r.name,
            "summary": f"returned {r.name}",
        })

    vstmt = (
        select(
            ItemVersion.created_at,
            ItemVersion.item_id,
            Item.name,
        )
        .select_from(ItemVersion)
        .join(Item, Item.id == ItemVersion.item_id)
        .where(Item.owner_id == owner_id, Item.is_deleted.is_(False))
        .order_by(ItemVersion.created_at.desc())
        .limit(limit)
    )
    for r in (await session.execute(vstmt)).all():
        entries.append({
            "kind": "item_version",
            "at": r.created_at,
            "item_id": r.item_id,
            "item_name": r.name,
            "summary": f"{r.name} snapshot",
        })

    entries.sort(key=lambda e: e["at"], reverse=True)
    return entries[:limit]
