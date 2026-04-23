from __future__ import annotations

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
from app.schemas.item import ItemCreate, ItemListResponse, ItemRead, ItemUpdate
from app.services import item_history_service, notifications_service
from app.services.visibility_service import visible_item_owner_ids


def _to_read(item: Item) -> ItemRead:
    return ItemRead.model_validate({
        "id": item.id,
        "name": item.name,
        "description": item.description,
        "quantity": item.quantity,
        "min_quantity": item.min_quantity,
        "notes": item.notes,
        "is_favorite": item.is_favorite,
        "image_id": item.image_id,
        "owner_id": item.owner_id,
        "owner_username": item.owner.username,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
        "category": item.category,
        "location": item.location,
        "tags": item.tags,
    })


async def toggle_favorite(
    session: AsyncSession, owner_id: UUID, item_id: UUID
) -> ItemRead:
    item = await items_repository.get_owned(session, owner_id, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="item not found")
    item.is_favorite = not item.is_favorite
    saved = await items_repository.save(session, item)
    return _to_read(saved)


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
    tag_ids: list[int] | None,
    favorite: bool | None = None,
    page: int,
    per_page: int,
) -> ItemListResponse:
    visible = await visible_item_owner_ids(session, owner_id)
    rows, total = await items_repository.list_paginated(
        session,
        visible,
        q=q,
        category_id=category_id,
        location_id=location_id,
        tag_ids=tag_ids,
        favorite=favorite,
        page=page,
        per_page=per_page,
    )
    return ItemListResponse(
        items=[_to_read(r) for r in rows],
        total=total,
        page=page,
        per_page=per_page,
    )


async def get_item(session: AsyncSession, owner_id: UUID, item_id: UUID) -> ItemRead:
    visible = await visible_item_owner_ids(session, owner_id)
    item = await items_repository.get_visible(session, visible, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="item not found")
    return _to_read(item)


async def create_item(session: AsyncSession, owner_id: UUID, body: ItemCreate) -> ItemRead:
    await _validate_refs(session, owner_id, body.category_id, body.location_id)
    tags = await tags_repository.get_or_create_many(session, owner_id, body.tag_names)
    item = Item(
        owner_id=owner_id,
        name=body.name,
        description=body.description,
        category_id=body.category_id,
        location_id=body.location_id,
        quantity=body.quantity,
        min_quantity=body.min_quantity,
        notes=body.notes,
        image_id=body.image_id,
        tags=tags,
    )
    created = await items_repository.create(session, item)
    if (
        created.min_quantity is not None
        and created.min_quantity > 0
        and created.quantity <= created.min_quantity
    ):
        await notifications_service.emit(
            session,
            user_id=owner_id,
            type="low_stock",
            title=f"「{created.name}」庫存不足",
            body=f"目前數量：{created.quantity}，提醒閾值：{created.min_quantity}",
            link=f"/items/{created.id}",
        )
    return _to_read(created)


async def update_item(
    session: AsyncSession, owner_id: UUID, item_id: UUID, body: ItemUpdate
) -> ItemRead:
    item = await items_repository.get_owned(session, owner_id, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="item not found")
    old_quantity = item.quantity
    # Snapshot pre-update state for version history
    pre_snapshot = {
        "name": item.name,
        "description": item.description,
        "quantity": item.quantity,
        "min_quantity": item.min_quantity,
        "notes": item.notes,
        "category_id": item.category_id,
        "location_id": item.location_id,
        "image_id": str(item.image_id) if item.image_id else None,
    }
    await item_history_service.snapshot_version(
        session, item_id=item.id, user_id=owner_id, snapshot=pre_snapshot,
    )
    fields = body.model_dump(exclude_unset=True)
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
        and saved.quantity <= saved.min_quantity
    ):
        await notifications_service.emit(
            session,
            user_id=owner_id,
            type="low_stock",
            title=f"「{saved.name}」庫存不足",
            body=f"目前數量：{saved.quantity}，提醒閾值：{saved.min_quantity}",
            link=f"/items/{saved.id}",
        )
    return _to_read(saved)


async def delete_item(session: AsyncSession, owner_id: UUID, item_id: UUID) -> None:
    item = await items_repository.get_owned(session, owner_id, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="item not found")
    await items_repository.soft_delete(session, item)
