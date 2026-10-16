from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.category import Category
from app.models.item import Item
from app.models.item_batch import ItemBatch
from app.models.location import Location
from app.models.tag import Tag
from app.models.warehouse import Warehouse
from app.repositories import locations_repository
from app.services import barcode_service


# Separator used in the pipe-delimited tag_names column ("kitchen|sharp|red").
TAG_SEPARATOR = "|"


EXPORT_COLUMNS = [
    "id",
    "name",
    "description",
    "barcode",
    "quantity",
    "min_quantity",
    "category_name",
    "location_path",
    "warehouse_name",
    "tag_names",
    "notes",
    "is_favorite",
    "created_at",
    "updated_at",
    "expiry_date",
]

# Optional columns recognized by the importer.
IMPORT_OPTIONAL = {
    "description",
    "barcode",
    "quantity",
    "min_quantity",
    "notes",
    "category_name",
    "location_path",
    # 舊檔相容（Phase 26 前的三欄格式；與 location_path 併為同一路徑邏輯）
    "location_floor",
    "location_room",
    "location_zone",
    "warehouse_name",
    "tag_names",
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
        .options(
            selectinload(Item.category),
            selectinload(Item.location),
            selectinload(Item.tags),
        )
    )
    rows = list((await session.execute(stmt)).scalars().all())

    # warehouse is a plain FK without a relationship on Item; fetch names in bulk
    wh_ids = {r.warehouse_id for r in rows if r.warehouse_id is not None}
    wh_names: dict[int, str] = {}
    if wh_ids:
        w_stmt = select(Warehouse).where(Warehouse.id.in_(wh_ids))
        for w in (await session.execute(w_stmt)).scalars().all():
            wh_names[w.id] = w.name

    # Phase 22 stretch：恰一筆未耗盡批次時帶出到期日（完整批次匯出留待後續）
    item_ids = [r.id for r in rows]
    single_batch_expiry: dict[UUID, date | None] = {}
    if item_ids:
        agg_stmt = (
            select(
                ItemBatch.item_id,
                func.count(ItemBatch.id),
                func.min(ItemBatch.expiry_date),
            )
            .where(
                ItemBatch.item_id.in_(item_ids),
                ItemBatch.is_depleted.is_(False),
            )
            .group_by(ItemBatch.item_id)
        )
        for item_id, batch_count, soonest in (await session.execute(agg_stmt)).all():
            if int(batch_count) == 1:
                single_batch_expiry[item_id] = soonest

    location_paths: dict[int, str] = {}
    if item_ids:
        location_ids = sorted({r.location_id for r in rows if r.location_id is not None})
        if location_ids:
            locations = await locations_repository.fetch_all(session, owner_id)
            location_paths = locations_repository.paths_for(locations, location_ids)

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=EXPORT_COLUMNS)
    writer.writeheader()
    for item in rows:
        tag_names = TAG_SEPARATOR.join(sorted(t.name for t in item.tags)) if item.tags else ""
        expiry_date = single_batch_expiry.get(item.id)
        writer.writerow({
            "id": str(item.id),
            "name": item.name,
            "description": item.description or "",
            "barcode": item.barcode or "",
            "quantity": item.quantity,
            "min_quantity": item.min_quantity if item.min_quantity is not None else "",
            "category_name": item.category.name if item.category else "",
            "location_path": (
                location_paths.get(item.location_id, "") if item.location_id else ""
            ),
            "warehouse_name": wh_names.get(item.warehouse_id) if item.warehouse_id else "",
            "tag_names": tag_names,
            "notes": item.notes or "",
            "is_favorite": "true" if item.is_favorite else "false",
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
            "expiry_date": expiry_date.isoformat() if expiry_date else "",
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


async def _ensure_tag(
    session: AsyncSession,
    owner_id: UUID,
    name: str,
    cache: dict[str, Tag],
) -> Tag:
    if name in cache:
        return cache[name]
    stmt = select(Tag).where(Tag.owner_id == owner_id, Tag.name == name)
    existing = (await session.execute(stmt)).scalar_one_or_none()
    if existing is not None:
        cache[name] = existing
        return existing
    tag = Tag(owner_id=owner_id, name=name)
    session.add(tag)
    await session.flush()
    cache[name] = tag
    return tag


def _parse_tag_names(raw: str | None) -> list[str]:
    """Split a pipe-delimited cell into a list of unique trimmed tag names.

    Empty cell → empty list. Duplicate entries are deduplicated while
    preserving first-seen order. Whitespace around each name is stripped.
    """
    if not raw:
        return []
    seen: set[str] = set()
    out: list[str] = []
    for piece in raw.split(TAG_SEPARATOR):
        name = piece.strip()
        if not name or name in seen:
            continue
        seen.add(name)
        out.append(name)
    return out


KIND_BY_DEPTH = {1: "floor", 2: "room"}


async def _ensure_location_path(
    session: AsyncSession,
    owner_id: UUID,
    parts: list[str],
    cache: dict[tuple[str, ...], int],
) -> int | None:
    """依路徑逐層建立／重用位置樹節點；回傳最深節點 id（無層級 → None）。

    深度 1→`floor`、2→`room`、≥3→`other`；快取以「路徑前綴」為鍵，同一匯入檔
    內共用中間節點。
    """
    normalized = [part.strip() for part in parts if part and part.strip()]
    if not normalized:
        return None
    parent_id: int | None = None
    for depth, name in enumerate(normalized, start=1):
        prefix = tuple(normalized[:depth])
        cached = cache.get(prefix)
        if cached is not None:
            parent_id = cached
            continue
        stmt = select(Location).where(
            Location.owner_id == owner_id, Location.name == name
        )
        stmt = (
            stmt.where(Location.parent_id.is_(None))
            if parent_id is None
            else stmt.where(Location.parent_id == parent_id)
        )
        existing = (await session.execute(stmt)).scalar_one_or_none()
        if existing is not None:
            node_id = existing.id
        else:
            node = Location(
                owner_id=owner_id,
                parent_id=parent_id,
                name=name,
                kind=KIND_BY_DEPTH.get(depth, "other"),
            )
            session.add(node)
            await session.flush()
            node_id = node.id
        cache[prefix] = node_id
        parent_id = node_id
    return parent_id


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
    loc_cache: dict[tuple[str, ...], int] = {}
    tag_cache: dict[str, Tag] = {}
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
        raw_path = (row.get("location_path") or "").strip()
        if raw_path:
            parts = raw_path.split("/")
        else:
            # 舊檔相容：三欄格式（floor/room/zone）併為同一路徑
            parts = [
                (row.get("location_floor") or "").strip(),
                (row.get("location_room") or "").strip(),
                (row.get("location_zone") or "").strip(),
            ]
        location_id = await _ensure_location_path(session, owner_id, parts, loc_cache)

        item = Item(
            owner_id=owner_id,
            name=name,
            description=(row.get("description") or "").strip() or None,
            barcode=barcode_service.canonicalize(
                (row.get("barcode") or "").strip()
            )
            or None,
            quantity=qty,
            min_quantity=min_qty,
            category_id=category_id,
            location_id=location_id,
            warehouse_id=warehouse_id,
            notes=(row.get("notes") or "").strip() or None,
        )

        tag_names = _parse_tag_names(row.get("tag_names"))
        if tag_names:
            tags = [
                await _ensure_tag(session, owner_id, tn, tag_cache) for tn in tag_names
            ]
            item.tags = tags

        session.add(item)
        to_create.append(item)

    if to_create:
        await session.commit()

    return ImportSummary(
        created_count=len(to_create),
        errors=errors,
        total_rows=total,
    )
