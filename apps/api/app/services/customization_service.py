from __future__ import annotations
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import delete as sa_delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customization import CustomField, ItemCustomValue, ItemTemplate, ItemType
from app.models.item import Item
from app.schemas.customization import (
    CustomFieldCreate,
    CustomFieldRead,
    ItemCustomValueRead,
    ItemCustomValueSet,
    ItemTemplateCreate,
    ItemTemplateRead,
    ItemTypeCreate,
    ItemTypeRead,
)


# --- item types ---
async def list_item_types(session: AsyncSession, owner_id: UUID) -> list[ItemTypeRead]:
    stmt = select(ItemType).where(ItemType.owner_id == owner_id).order_by(ItemType.name)
    rows = (await session.execute(stmt)).scalars().all()
    return [ItemTypeRead.model_validate(r) for r in rows]


async def create_item_type(
    session: AsyncSession, owner_id: UUID, body: ItemTypeCreate
) -> ItemTypeRead:
    try:
        t = ItemType(owner_id=owner_id, name=body.name, icon=body.icon)
        session.add(t)
        await session.commit()
        await session.refresh(t)
        return ItemTypeRead.model_validate(t)
    except Exception:
        await session.rollback()
        raise HTTPException(status_code=409, detail="name already exists")


async def delete_item_type(session: AsyncSession, owner_id: UUID, type_id: int) -> None:
    stmt = sa_delete(ItemType).where(ItemType.id == type_id, ItemType.owner_id == owner_id)
    result = await session.execute(stmt)
    await session.commit()
    if (result.rowcount or 0) == 0:
        raise HTTPException(status_code=404, detail="type not found")


# --- custom fields ---
async def list_custom_fields(session: AsyncSession, owner_id: UUID) -> list[CustomFieldRead]:
    stmt = select(CustomField).where(CustomField.owner_id == owner_id).order_by(CustomField.name)
    rows = (await session.execute(stmt)).scalars().all()
    return [CustomFieldRead.model_validate(r) for r in rows]


async def create_custom_field(
    session: AsyncSession, owner_id: UUID, body: CustomFieldCreate
) -> CustomFieldRead:
    try:
        f = CustomField(owner_id=owner_id, name=body.name, field_type=body.field_type)
        session.add(f)
        await session.commit()
        await session.refresh(f)
        return CustomFieldRead.model_validate(f)
    except Exception:
        await session.rollback()
        raise HTTPException(status_code=409, detail="name already exists")


async def delete_custom_field(session: AsyncSession, owner_id: UUID, field_id: int) -> None:
    stmt = sa_delete(CustomField).where(
        CustomField.id == field_id, CustomField.owner_id == owner_id
    )
    result = await session.execute(stmt)
    await session.commit()
    if (result.rowcount or 0) == 0:
        raise HTTPException(status_code=404, detail="field not found")


# --- item custom values ---
async def _ensure_item(session: AsyncSession, owner_id: UUID, item_id: UUID) -> Item:
    item = (await session.execute(
        select(Item).where(
            Item.id == item_id, Item.owner_id == owner_id, Item.is_deleted.is_(False)
        )
    )).scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="item not found")
    return item


async def get_item_custom_values(
    session: AsyncSession, owner_id: UUID, item_id: UUID
) -> list[ItemCustomValueRead]:
    await _ensure_item(session, owner_id, item_id)
    rows = (await session.execute(
        select(ItemCustomValue).where(ItemCustomValue.item_id == item_id)
    )).scalars().all()
    return [ItemCustomValueRead.model_validate(r) for r in rows]


async def set_item_custom_value(
    session: AsyncSession, owner_id: UUID, item_id: UUID, body: ItemCustomValueSet
) -> ItemCustomValueRead:
    await _ensure_item(session, owner_id, item_id)
    # verify field belongs to owner
    field = await session.get(CustomField, body.custom_field_id)
    if field is None or field.owner_id != owner_id:
        raise HTTPException(status_code=404, detail="custom field not found")
    # upsert
    existing = (await session.execute(
        select(ItemCustomValue).where(
            ItemCustomValue.item_id == item_id,
            ItemCustomValue.custom_field_id == body.custom_field_id,
        )
    )).scalar_one_or_none()
    # Wrap primitives in dict since the column stores JSON
    stored = {"v": body.value} if body.value is not None else None
    if existing is None:
        row = ItemCustomValue(
            item_id=item_id, custom_field_id=body.custom_field_id, value=stored,
        )
        session.add(row)
    else:
        existing.value = stored
        row = existing
    await session.commit()
    return ItemCustomValueRead(
        custom_field_id=body.custom_field_id, value=body.value,
    )


async def delete_item_custom_value(
    session: AsyncSession, owner_id: UUID, item_id: UUID, field_id: int
) -> None:
    await _ensure_item(session, owner_id, item_id)
    stmt = sa_delete(ItemCustomValue).where(
        ItemCustomValue.item_id == item_id,
        ItemCustomValue.custom_field_id == field_id,
    )
    result = await session.execute(stmt)
    await session.commit()
    if (result.rowcount or 0) == 0:
        raise HTTPException(status_code=404, detail="value not set")


# --- item templates ---
async def list_templates(session: AsyncSession, owner_id: UUID) -> list[ItemTemplateRead]:
    stmt = select(ItemTemplate).where(ItemTemplate.owner_id == owner_id).order_by(ItemTemplate.name)
    rows = (await session.execute(stmt)).scalars().all()
    return [ItemTemplateRead.model_validate(r) for r in rows]


async def create_template(
    session: AsyncSession, owner_id: UUID, body: ItemTemplateCreate
) -> ItemTemplateRead:
    try:
        t = ItemTemplate(owner_id=owner_id, name=body.name, payload=body.payload)
        session.add(t)
        await session.commit()
        await session.refresh(t)
        return ItemTemplateRead.model_validate(t)
    except Exception:
        await session.rollback()
        raise HTTPException(status_code=409, detail="name already exists")


async def delete_template(session: AsyncSession, owner_id: UUID, template_id: int) -> None:
    stmt = sa_delete(ItemTemplate).where(
        ItemTemplate.id == template_id, ItemTemplate.owner_id == owner_id
    )
    result = await session.execute(stmt)
    await session.commit()
    if (result.rowcount or 0) == 0:
        raise HTTPException(status_code=404, detail="template not found")
