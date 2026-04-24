from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.category import Category
from app.models.item import Item
from app.models.location import Location
from app.models.warehouse import Warehouse


EXPORT_COLUMNS = [
    "id",
    "name",
    "description",
    "quantity",
    "min_quantity",
    "category_name",
    "location_floor",
    "location_room",
    "location_zone",
    "warehouse_name",
    "notes",
    "is_favorite",
    "created_at",
    "updated_at",
]

# Optional columns recognized by the importer.
IMPORT_OPTIONAL = {
    "description",
    "quantity",
    "min_quantity",
    "notes",
    "category_name",
    "location_floor",
    "location_room",
    "location_zone",
    "warehouse_name",
}


@dataclass
class RowError:
    row: int  # 1-indexed, matching the user's CSV file (header is row 1)
    reason: str


@dataclass
class ImportSummary:
    created_count: int
    errors: list[RowError]
    total_rows: int


# ---------- export --------------------------------------------------------


async def export_csv(session: AsyncSession, owner_id: UUID) -> str:
    stmt = (
        select(Item)
        .where(Item.owner_id == owner_id, Item.is_deleted.is_(False))
        .order_by(Item.created_at.asc())
        .options(selectinload(Item.category), selectinload(Item.location))
    )
    rows = list((await session.execute(stmt)).scalars().all())

    # warehouse is a plain FK without a relationship on Item; fetch names in bulk
    wh_ids = {r.warehouse_id for r in rows if r.warehouse_id is not None}
    wh_names: dict[int, str] = {}
    if wh_ids:
        w_stmt = select(Warehouse).where(Warehouse.id.in_(wh_ids))
        for w in (await session.execute(w_stmt)).scalars().all():
            wh_names[w.id] = w.name

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=EXPORT_COLUMNS)
    writer.writeheader()
    for item in rows:
        loc = item.location
        writer.writerow({
            "id": str(item.id),
            "name": item.name,
            "description": item.description or "",
            "quantity": item.quantity,
            "min_quantity": item.min_quantity if item.min_quantity is not None else "",
            "category_name": item.category.name if item.category else "",
            "location_floor": loc.floor if loc else "",
            "location_room": loc.room if loc and loc.room else "",
            "location_zone": loc.zone if loc and loc.zone else "",
            "warehouse_name": wh_names.get(item.warehouse_id) if item.warehouse_id else "",
            "notes": item.notes or "",
            "is_favorite": "true" if item.is_favorite else "false",
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
        })
    return buf.getvalue()


# ---------- import --------------------------------------------------------


def _parse_int(raw: str | None) -> int | None:
    if raw is None or raw == "":
        return None
    return int(raw)


async def _ensure_category(
    session: AsyncSession,
    owner_id: UUID,
    name: str,
    cache: dict[str, int],
) -> int:
    if name in cache:
        return cache[name]
    stmt = select(Category).where(
        Category.owner_id == owner_id, Category.name == name
    )
    existing = (await session.execute(stmt)).scalar_one_or_none()
    if existing is not None:
        cache[name] = existing.id
        return existing.id
    cat = Category(owner_id=owner_id, name=name, parent_id=None)
    session.add(cat)
    await session.flush()
    cache[name] = cat.id
    return cat.id


async def _ensure_warehouse(
    session: AsyncSession,
    owner_id: UUID,
    name: str,
    cache: dict[str, int],
) -> int:
    if name in cache:
        return cache[name]
    stmt = select(Warehouse).where(
        Warehouse.owner_id == owner_id, Warehouse.name == name
    )
    existing = (await session.execute(stmt)).scalar_one_or_none()
    if existing is not None:
        cache[name] = existing.id
        return existing.id
    wh = Warehouse(owner_id=owner_id, name=name)
    session.add(wh)
    await session.flush()
    cache[name] = wh.id
    return wh.id


async def _ensure_location(
    session: AsyncSession,
    owner_id: UUID,
    floor: str,
    room: str | None,
    zone: str | None,
    cache: dict[tuple[str, str | None, str | None], int],
) -> int:
    key = (floor, room or None, zone or None)
    if key in cache:
        return cache[key]
    stmt = select(Location).where(
        Location.owner_id == owner_id,
        Location.floor == floor,
        Location.room == (room if room else None),
        Location.zone == (zone if zone else None),
    )
    existing = (await session.execute(stmt)).scalar_one_or_none()
    if existing is not None:
        cache[key] = existing.id
        return existing.id
    loc = Location(owner_id=owner_id, floor=floor, room=room or None, zone=zone or None)
    session.add(loc)
    await session.flush()
    cache[key] = loc.id
    return loc.id


async def import_csv(
    session: AsyncSession, owner_id: UUID, raw_bytes: bytes
) -> ImportSummary:
    """Parse CSV bytes and create items for each valid row.

    Partial-success model: every row is validated independently. Rows that
    fail validation are reported in `errors`. Valid rows are persisted in a
    single commit at the end for performance.
    """
    try:
        text = raw_bytes.decode("utf-8-sig")  # tolerate BOM
    except UnicodeDecodeError as exc:
        return ImportSummary(
            created_count=0,
            errors=[RowError(row=0, reason=f"file not utf-8: {exc}")],
            total_rows=0,
        )

    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None or "name" not in reader.fieldnames:
        return ImportSummary(
            created_count=0,
            errors=[RowError(row=1, reason="required column 'name' missing")],
            total_rows=0,
        )

    errors: list[RowError] = []
    to_create: list[Item] = []
    cat_cache: dict[str, int] = {}
    wh_cache: dict[str, int] = {}
    loc_cache: dict[tuple[str, str | None, str | None], int] = {}
    total = 0

    for idx, row in enumerate(reader, start=2):  # start=2 because row 1 is header
        total += 1
        name = (row.get("name") or "").strip()
        if not name:
            errors.append(RowError(row=idx, reason="name is required"))
            continue

        try:
            qty = _parse_int((row.get("quantity") or "").strip()) or 1
            if qty < 0:
                raise ValueError("quantity must be >= 0")
            min_qty = _parse_int((row.get("min_quantity") or "").strip())
            if min_qty is not None and min_qty < 0:
                raise ValueError("min_quantity must be >= 0")
        except ValueError as exc:
            errors.append(RowError(row=idx, reason=str(exc)))
            continue

        category_id: int | None = None
        cat_name = (row.get("category_name") or "").strip()
        if cat_name:
            category_id = await _ensure_category(session, owner_id, cat_name, cat_cache)

        warehouse_id: int | None = None
        wh_name = (row.get("warehouse_name") or "").strip()
        if wh_name:
            warehouse_id = await _ensure_warehouse(
                session, owner_id, wh_name, wh_cache
            )

        location_id: int | None = None
        floor = (row.get("location_floor") or "").strip()
        if floor:
            location_id = await _ensure_location(
                session,
                owner_id,
                floor,
                (row.get("location_room") or "").strip() or None,
                (row.get("location_zone") or "").strip() or None,
                loc_cache,
            )

        item = Item(
            owner_id=owner_id,
            name=name,
            description=(row.get("description") or "").strip() or None,
            quantity=qty,
            min_quantity=min_qty,
            category_id=category_id,
            location_id=location_id,
            warehouse_id=warehouse_id,
            notes=(row.get("notes") or "").strip() or None,
        )
        session.add(item)
        to_create.append(item)

    if to_create:
        await session.commit()

    return ImportSummary(
        created_count=len(to_create),
        errors=errors,
        total_rows=total,
    )
