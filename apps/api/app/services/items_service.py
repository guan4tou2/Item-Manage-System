from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.item import Item
from app.repositories import (
    categories_repository,
    items_repository,
    locations_repository,
    tags_repository,
)
from app.schemas.item import (
    ItemBulkDelete,
    ItemBulkResult,
    ItemBulkUpdate,
    ItemCreate,
    ItemListResponse,
    ItemRead,
    ItemUpdate,
)
from app.services import (
    barcode_service,
    item_history_service,
    notifications_service,
    webhooks_service,
)
from app.services.visibility_service import visible_item_owner_ids


def _location_view(loc, *, path: str | None) -> dict:
    return {
        "id": loc.id,
        "parent_id": loc.parent_id,
        "name": loc.name,
        "kind": loc.kind,
        "sort_order": loc.sort_order,
        "floor_plan_image_id": loc.floor_plan_image_id,
        "path": path or loc.name,
    }


async def _paths_for_items(session: AsyncSession, items) -> dict[int, str]:
    """item 所屬 owner 的位置樹路徑（物品可能屬於他人：共享清單／群組可見）。"""
    by_owner: dict[UUID, set[int]] = {}
    for item in items:
        if item.location_id is None:
            continue
        by_owner.setdefault(item.owner_id, set()).add(item.location_id)
    if not by_owner:
        return {}
    out: dict[int, str] = {}
    for owner, location_ids in by_owner.items():
        locations = await locations_repository.fetch_all(session, owner)
        out.update(locations_repository.paths_for(locations, sorted(location_ids)))
    return out


def _to_read(
    item: Item,
    *,
    soonest_expiry: date | None = None,
    location_path: str | None = None,
) -> ItemRead:
    return ItemRead.model_validate({
        "id": item.id,
        "name": item.name,
        "description": item.description,
        "barcode": item.barcode,
        "quantity": item.quantity,
        "min_quantity": item.min_quantity,
        "cost": item.cost,
        "track_batches": item.track_batches,
        "soonest_expiry": soonest_expiry,
        "notes": item.notes,
        "is_favorite": item.is_favorite,
        "image_id": item.image_id,
        "warehouse_id": item.warehouse_id,
        "owner_id": item.owner_id,
        "owner_username": item.owner.username,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
        "category": item.category,
        "location": (
            _location_view(item.location, path=location_path)
            if item.location is not None
            else None
        ),
        "tags": item.tags,
    })


async def _read_with_location(
    session: AsyncSession, item: Item, *, soonest_expiry: date | None = None
) -> ItemRead:
    paths = await _paths_for_items(session, [item])
    path = paths.get(item.location_id) if item.location_id is not None else None
    return _to_read(item, soonest_expiry=soonest_expiry, location_path=path)


async def toggle_favorite(
    session: AsyncSession, owner_id: UUID, item_id: UUID
) -> ItemRead:
    item = await items_repository.get_owned(session, owner_id, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="item not found")
    item.is_favorite = not item.is_favorite
    saved = await items_repository.save(session, item)
    return await _read_with_location(session, saved)


async def _validate_refs(
    session: AsyncSession,
    owner_id: UUID,
    category_id: int | None,
    location_id: int | None,
) -> None:
    if category_id is not None:
        if await categories_repository.get_owned(session, owner_id, category_id) is None:
            raise HTTPException(status_code=422, detail="category_id not found")
    if location_id is not None:
        if await locations_repository.get_owned(session, owner_id, location_id) is None:
            raise HTTPException(status_code=422, detail="location_id not found")


async def list_items(
    session: AsyncSession,
    owner_id: UUID,
    *,
    q: str | None,
    category_id: int | None,
    location_id: int | None,
    location_scope: str = "subtree",
    warehouse_id: int | None = None,
    tag_ids: list[int] | None,
    favorite: bool | None = None,
    expiry: str | None = None,
    sort: str | None = None,
    page: int,
    per_page: int,
) -> ItemListResponse:
    visible = await visible_item_owner_ids(session, owner_id)
    resolved_location_ids: list[int] | None = None
    if location_id is not None:
        if location_scope == "exact":
            resolved_location_ids = [location_id]
        else:
            # 預設含子孫；節點不存在／非本人 → 空集合（明確無結果）
            resolved_location_ids = sorted(
                await locations_repository.descendant_ids(
                    session, owner_id, [location_id]
                )
            )
    rows, total = await items_repository.list_paginated(
        session,
        visible,
        q=q,
        category_id=category_id,
        location_ids=resolved_location_ids,
        warehouse_id=warehouse_id,
        tag_ids=tag_ids,
        favorite=favorite,
        expiry=expiry,
        sort=sort,
        page=page,
        per_page=per_page,
    )
    paths = await _paths_for_items(session, [row[0] for row in rows])
    return ItemListResponse(
        items=[
            _to_read(
                row[0],
                soonest_expiry=row[1],
                location_path=(
                    paths.get(row[0].location_id)
                    if row[0].location_id is not None
                    else None
                ),
            )
            for row in rows
        ],
        total=total,
        page=page,
        per_page=per_page,
    )


async def get_item(session: AsyncSession, owner_id: UUID, item_id: UUID) -> ItemRead:
    visible = await visible_item_owner_ids(session, owner_id)
    item = await items_repository.get_visible(session, visible, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="item not found")
    return await _read_with_location(session, item)


async def create_item(session: AsyncSession, owner_id: UUID, body: ItemCreate) -> ItemRead:
    await _validate_refs(session, owner_id, body.category_id, body.location_id)
    tags = await tags_repository.get_or_create_many(session, owner_id, body.tag_names)
    item = Item(
        owner_id=owner_id,
        name=body.name,
        description=body.description,
        barcode=barcode_service.canonicalize(body.barcode) or None,
        category_id=body.category_id,
        location_id=body.location_id,
        warehouse_id=body.warehouse_id,
        quantity=body.quantity,
        min_quantity=body.min_quantity,
        cost=body.cost,
        notes=body.notes,
        image_id=body.image_id,
        tags=tags,
    )
    created = await items_repository.create(session, item)
    if (
        created.min_quantity is not None
        and created.min_quantity > 0
        and created.quantity < created.min_quantity
    ):
        await notifications_service.emit(
            session,
            user_id=owner_id,
            type="low_stock",
            title=f"「{created.name}」庫存不足",
            body=f"目前數量：{created.quantity}，提醒閾值：{created.min_quantity}",
            link=f"/items/{created.id}",
        )
    result = await _read_with_location(session, created)
    await webhooks_service.dispatch(
        session, owner_id, "item.created",
        {"id": str(created.id), "name": created.name},
    )
    return result


async def update_item(
    session: AsyncSession, owner_id: UUID, item_id: UUID, body: ItemUpdate
) -> ItemRead:
    item = await items_repository.get_owned(session, owner_id, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="item not found")
    fields = body.model_dump(exclude_unset=True)
    if "barcode" in fields:
        fields["barcode"] = barcode_service.canonicalize(fields["barcode"]) or None
    if item.track_batches and "quantity" in fields:
        raise HTTPException(
            status_code=409,
            detail="item tracks batches; change quantity via batch endpoints",
        )
    old_quantity = item.quantity
    # Snapshot pre-update state for version history
    pre_snapshot = {
        "name": item.name,
        "description": item.description,
        "quantity": item.quantity,
        "min_quantity": item.min_quantity,
        "cost": str(item.cost) if item.cost is not None else None,
        "notes": item.notes,
        "category_id": item.category_id,
        "location_id": item.location_id,
        "image_id": str(item.image_id) if item.image_id else None,
    }
    await item_history_service.snapshot_version(
        session, item_id=item.id, user_id=owner_id, snapshot=pre_snapshot,
    )
    quantity_changing = "quantity" in fields
    if "category_id" in fields or "location_id" in fields:
        await _validate_refs(
            session,
            owner_id,
            fields.get("category_id", item.category_id),
            fields.get("location_id", item.location_id),
        )
    if "tag_names" in fields:
        new_names = fields.pop("tag_names")
        item.tags = await tags_repository.get_or_create_many(session, owner_id, new_names or [])
    for k, v in fields.items():
        setattr(item, k, v)
    saved = await items_repository.save(session, item)
    if quantity_changing and saved.quantity != old_quantity:
        await item_history_service.log_quantity_change(
            session,
            item_id=saved.id,
            user_id=owner_id,
            old_quantity=old_quantity,
            new_quantity=saved.quantity,
        )
    if (
        quantity_changing
        and saved.min_quantity is not None
        and saved.min_quantity > 0
        and old_quantity > saved.min_quantity
        and saved.quantity < saved.min_quantity
    ):
        await notifications_service.emit(
            session,
            user_id=owner_id,
            type="low_stock",
            title=f"「{saved.name}」庫存不足",
            body=f"目前數量：{saved.quantity}，提醒閾值：{saved.min_quantity}",
            link=f"/items/{saved.id}",
        )
    result = await _read_with_location(session, saved)
    await webhooks_service.dispatch(
        session, owner_id, "item.updated",
        {"id": str(saved.id), "name": saved.name},
    )
    return result


def _unique_item_ids(item_ids: list[UUID]) -> list[UUID]:
    seen: set[UUID] = set()
    unique: list[UUID] = []
    for item_id in item_ids:
        if item_id in seen:
            continue
        seen.add(item_id)
        unique.append(item_id)
    return unique


async def _get_owned_items_or_404(
    session: AsyncSession,
    owner_id: UUID,
    item_ids: list[UUID],
) -> list[Item]:
    items: list[Item] = []
    for item_id in _unique_item_ids(item_ids):
        item = await items_repository.get_owned(session, owner_id, item_id)
        if item is None:
            raise HTTPException(status_code=404, detail="item not found")
        items.append(item)
    return items


async def bulk_update_items(
    session: AsyncSession,
    owner_id: UUID,
    body: ItemBulkUpdate,
) -> ItemBulkResult:
    items = await _get_owned_items_or_404(session, owner_id, body.item_ids)
    fields_set = body.model_fields_set

    if "category_id" in fields_set or "location_id" in fields_set:
        await _validate_refs(
            session,
            owner_id,
            body.category_id if "category_id" in fields_set else None,
            body.location_id if "location_id" in fields_set else None,
        )

    tags = None
    if "tag_names" in fields_set:
        tags = await tags_repository.get_or_create_many(session, owner_id, body.tag_names or [])

    for item in items:
        if "category_id" in fields_set:
            item.category_id = body.category_id
        if "location_id" in fields_set:
            item.location_id = body.location_id
        if tags is not None:
            if body.tag_mode == "append":
                merged = {tag.name: tag for tag in item.tags}
                for tag in tags:
                    merged[tag.name] = tag
                item.tags = list(merged.values())
            else:
                item.tags = tags

    await session.commit()
    for item in items:
        await webhooks_service.dispatch(
            session, owner_id, "item.updated",
            {"id": str(item.id), "name": item.name},
        )
    return ItemBulkResult(updated=len(items))


async def bulk_delete_items(
    session: AsyncSession,
    owner_id: UUID,
    body: ItemBulkDelete,
) -> ItemBulkResult:
    items = await _get_owned_items_or_404(session, owner_id, body.item_ids)
    for item in items:
        item.is_deleted = True
    await session.commit()
    for item in items:
        await webhooks_service.dispatch(
            session, owner_id, "item.deleted",
            {"id": str(item.id), "name": item.name},
        )
    return ItemBulkResult(deleted=len(items))


async def delete_item(session: AsyncSession, owner_id: UUID, item_id: UUID) -> None:
    item = await items_repository.get_owned(session, owner_id, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="item not found")
    await items_repository.soft_delete(session, item)
    await webhooks_service.dispatch(
        session, owner_id, "item.deleted",
        {"id": str(item.id), "name": item.name},
    )
