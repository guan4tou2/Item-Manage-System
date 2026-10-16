from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.item import Item
from app.models.location import Location


async def fetch_all(session: AsyncSession, owner_id: UUID) -> list[Location]:
    """owner 全部節點（原始列；排序與走訪序由 `walk_order` 決定）。"""
    stmt = (
        select(Location)
        .where(Location.owner_id == owner_id)
        .order_by(Location.sort_order, Location.name, Location.id)
    )
    return list((await session.execute(stmt)).scalars().all())


def walk_order(locations: list[Location]) -> list[Location]:
    """深度優先走訪序：同層依 (sort_order, name, id)。"""
    children: dict[int | None, list[Location]] = {}
    for loc in locations:
        children.setdefault(loc.parent_id, []).append(loc)
    for group in children.values():
        group.sort(key=lambda node: (node.sort_order, node.name, node.id))

    ordered: list[Location] = []

    def visit(node: Location) -> None:
        ordered.append(node)
        for child in children.get(node.id, []):
            visit(child)

    for root in children.get(None, []):
        visit(root)
    # 防禦：parent 缺失（理論上不會發生）的節點仍列出，避免靜默遺漏
    seen = {node.id for node in ordered}
    for loc in locations:
        if loc.id not in seen:
            visit(loc)
    return ordered


def path_for(locations: list[Location], location_id: int) -> str | None:
    by_id = {loc.id: loc for loc in locations}
    node = by_id.get(location_id)
    if node is None:
        return None
    parts: list[str] = []
    guard = 0
    while node is not None and guard < 64:
        parts.append(node.name)
        node = by_id.get(node.parent_id) if node.parent_id is not None else None
        guard += 1
    return " / ".join(reversed(parts))


def paths_for(locations: list[Location], location_ids: list[int]) -> dict[int, str]:
    out: dict[int, str] = {}
    for location_id in location_ids:
        path = path_for(locations, location_id)
        if path is not None:
            out[location_id] = path
    return out


async def get_owned(
    session: AsyncSession, owner_id: UUID, location_id: int
) -> Location | None:
    stmt = select(Location).where(
        Location.id == location_id, Location.owner_id == owner_id
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def descendant_ids(
    session: AsyncSession, owner_id: UUID, root_ids: list[int]
) -> set[int]:
    """含自身的子孫集合（recursive CTE；PG／SQLite 通用）。"""
    if not root_ids:
        return set()
    base = (
        select(Location.id)
        .where(Location.owner_id == owner_id, Location.id.in_(root_ids))
        .cte("descendants", recursive=True)
    )
    base = base.union_all(
        select(Location.id).where(
            Location.owner_id == owner_id, Location.parent_id == base.c.id
        )
    )
    return set((await session.execute(select(base.c.id))).scalars().all())


async def children_of(
    session: AsyncSession, owner_id: UUID, parent_id: int | None
) -> list[Location]:
    stmt = select(Location).where(Location.owner_id == owner_id)
    stmt = (
        stmt.where(Location.parent_id.is_(None))
        if parent_id is None
        else stmt.where(Location.parent_id == parent_id)
    )
    stmt = stmt.order_by(Location.sort_order, Location.name, Location.id)
    return list((await session.execute(stmt)).scalars().all())


async def sibling_with_name(
    session: AsyncSession,
    owner_id: UUID,
    parent_id: int | None,
    name: str,
    *,
    exclude_id: int | None = None,
) -> Location | None:
    stmt = select(Location).where(Location.owner_id == owner_id, Location.name == name)
    stmt = (
        stmt.where(Location.parent_id.is_(None))
        if parent_id is None
        else stmt.where(Location.parent_id == parent_id)
    )
    if exclude_id is not None:
        stmt = stmt.where(Location.id != exclude_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def item_counts(session: AsyncSession, owner_id: UUID) -> dict[int, int]:
    """各節點的**直接**物品數（未刪除）。"""
    stmt = (
        select(Item.location_id, func.count(Item.id))
        .where(
            Item.owner_id == owner_id,
            Item.is_deleted.is_(False),
            Item.location_id.is_not(None),
        )
        .group_by(Item.location_id)
    )
    return {int(row[0]): int(row[1]) for row in (await session.execute(stmt)).all()}


async def count_items(
    session: AsyncSession, owner_id: UUID, location_id: int
) -> int:
    stmt = select(func.count(Item.id)).where(
        Item.owner_id == owner_id,
        Item.location_id == location_id,
        Item.is_deleted.is_(False),
    )
    return int((await session.execute(stmt)).scalar_one())


async def count_children(
    session: AsyncSession, owner_id: UUID, location_id: int
) -> int:
    stmt = select(func.count(Location.id)).where(
        Location.owner_id == owner_id, Location.parent_id == location_id
    )
    return int((await session.execute(stmt)).scalar_one())


async def create(session: AsyncSession, owner_id: UUID, **fields) -> Location:
    loc = Location(owner_id=owner_id, **fields)
    session.add(loc)
    await session.commit()
    await session.refresh(loc)
    return loc


async def update(session: AsyncSession, loc: Location, **fields) -> Location:
    for key, value in fields.items():
        setattr(loc, key, value)
    await session.commit()
    await session.refresh(loc)
    return loc


async def delete(session: AsyncSession, loc: Location) -> None:
    await session.delete(loc)
    await session.commit()


async def set_sort_orders(
    session: AsyncSession, locations: list[Location], ordered_ids: list[int]
) -> None:
    by_id = {loc.id: loc for loc in locations}
    for index, location_id in enumerate(ordered_ids):
        by_id[location_id].sort_order = index
    await session.commit()
