from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.location import Location
from app.repositories import locations_repository as repo
from app.schemas.location import LocationCreate, LocationUpdate


def _view(loc: Location, path: str | None, item_count: int = 0) -> dict[str, Any]:
    return {
        "id": loc.id,
        "parent_id": loc.parent_id,
        "name": loc.name,
        "kind": loc.kind,
        "sort_order": loc.sort_order,
        "floor_plan_image_id": loc.floor_plan_image_id,
        "path": path or loc.name,
        "item_count": item_count,
    }


def _not_found(what: str = "location") -> HTTPException:
    return HTTPException(status_code=404, detail=f"{what} not found")


async def _require_owned(
    session: AsyncSession, owner_id: UUID, location_id: int
) -> Location:
    loc = await repo.get_owned(session, owner_id, location_id)
    if loc is None:
        raise _not_found()
    return loc


async def _require_parent(
    session: AsyncSession, owner_id: UUID, parent_id: int | None
) -> None:
    if parent_id is None:
        return
    parent = await repo.get_owned(session, owner_id, parent_id)
    if parent is None:
        raise _not_found("parent location")


async def _assert_no_duplicate_sibling(
    session: AsyncSession,
    owner_id: UUID,
    parent_id: int | None,
    name: str,
    *,
    exclude_id: int | None = None,
) -> None:
    existing = await repo.sibling_with_name(
        session, owner_id, parent_id, name, exclude_id=exclude_id
    )
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail={"code": "duplicate_name", "name": name},
        )


async def _assert_no_cycle(
    session: AsyncSession, owner_id: UUID, location_id: int, new_parent_id: int | None
) -> None:
    if new_parent_id is None:
        return
    if new_parent_id == location_id:
        raise HTTPException(status_code=422, detail={"code": "cycle"})
    descendants = await repo.descendant_ids(session, owner_id, [location_id])
    if new_parent_id in descendants:
        raise HTTPException(status_code=422, detail={"code": "cycle"})


async def list_all(session: AsyncSession, owner_id: UUID) -> list[dict[str, Any]]:
    """平坦清單（走訪序）＋完整路徑——供選擇器／篩選／行動版搜尋。"""
    locations = await repo.fetch_all(session, owner_id)
    counts = await repo.item_counts(session, owner_id)
    out: list[dict[str, Any]] = []
    for loc in repo.walk_order(locations):
        out.append(_view(loc, repo.path_for(locations, loc.id), counts.get(loc.id, 0)))
    return out


async def tree(session: AsyncSession, owner_id: UUID) -> list[dict[str, Any]]:
    """巢狀樹（root 陣列），節點附**直接**物品數 `item_count`。"""
    locations = await repo.fetch_all(session, owner_id)
    counts = await repo.item_counts(session, owner_id)
    children: dict[int | None, list[Location]] = {}
    for loc in locations:
        children.setdefault(loc.parent_id, []).append(loc)
    for group in children.values():
        group.sort(key=lambda node: (node.sort_order, node.name, node.id))

    def build(node: Location) -> dict[str, Any]:
        view = _view(
            node,
            repo.path_for(locations, node.id),
            counts.get(node.id, 0),
        )
        view["children"] = [build(child) for child in children.get(node.id, [])]
        return view

    return [build(root) for root in children.get(None, [])]


async def path_of(
    session: AsyncSession, owner_id: UUID, location_id: int
) -> dict[str, Any]:
    await _require_owned(session, owner_id, location_id)
    locations = await repo.fetch_all(session, owner_id)
    nodes: list[dict[str, Any]] = []
    by_id = {loc.id: loc for loc in locations}
    node = by_id.get(location_id)
    guard = 0
    while node is not None and guard < 64:
        nodes.append({"id": node.id, "name": node.name, "kind": node.kind})
        node = by_id.get(node.parent_id) if node.parent_id is not None else None
        guard += 1
    nodes.reverse()
    return {
        "id": location_id,
        "path": " / ".join(n["name"] for n in nodes),
        "nodes": nodes,
    }


async def create(
    session: AsyncSession, owner_id: UUID, body: LocationCreate
) -> dict[str, Any]:
    await _require_parent(session, owner_id, body.parent_id)
    await _assert_no_duplicate_sibling(session, owner_id, body.parent_id, body.name)
    fields = body.model_dump()
    loc = await repo.create(session, owner_id, **fields)
    locations = await repo.fetch_all(session, owner_id)
    return _view(loc, repo.path_for(locations, loc.id))


async def update(
    session: AsyncSession, owner_id: UUID, location_id: int, body: LocationUpdate
) -> dict[str, Any]:
    loc = await _require_owned(session, owner_id, location_id)
    fields = body.model_dump(exclude_unset=True)

    target_parent = fields.get("parent_id", loc.parent_id)
    if "parent_id" in fields:
        await _require_parent(session, owner_id, fields["parent_id"])
        await _assert_no_cycle(session, owner_id, location_id, fields["parent_id"])

    new_name = fields.get("name", loc.name)
    if "name" in fields or "parent_id" in fields:
        await _assert_no_duplicate_sibling(
            session,
            owner_id,
            target_parent,
            new_name,
            exclude_id=location_id,
        )

    loc = await repo.update(session, loc, **fields)
    locations = await repo.fetch_all(session, owner_id)
    return _view(loc, repo.path_for(locations, loc.id))


async def reorder(
    session: AsyncSession,
    owner_id: UUID,
    parent_id: int | None,
    location_ids: list[int],
) -> list[dict[str, Any]]:
    """重寫**同一 parent** 下子節點的 sort_order（需為完整子集合）。"""
    if len(set(location_ids)) != len(location_ids):
        raise HTTPException(status_code=422, detail={"code": "duplicate_ids"})
    await _require_parent(session, owner_id, parent_id)
    siblings = await repo.children_of(session, owner_id, parent_id)
    if {loc.id for loc in siblings} != set(location_ids):
        raise HTTPException(status_code=422, detail={"code": "invalid_siblings"})
    await repo.set_sort_orders(session, siblings, location_ids)
    return await list_all(session, owner_id)


async def delete(session: AsyncSession, owner_id: UUID, location_id: int) -> None:
    loc = await _require_owned(session, owner_id, location_id)
    children = await repo.count_children(session, owner_id, location_id)
    items = await repo.count_items(session, owner_id, location_id)
    if children > 0 or items > 0:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "has_children" if children > 0 else "has_items",
                "items": items,
                "children": children,
            },
        )
    await repo.delete(session, loc)
