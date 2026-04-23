from __future__ import annotations
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.category import Category
from app.models.customization import CustomField, ItemCustomValue, ItemTemplate, ItemType
from app.models.group import Group, GroupMember
from app.models.item import Item
from app.models.list import List as UserList, ListEntry
from app.models.location import Location
from app.models.tag import Tag
from app.models.warehouse import Warehouse


def _serialize(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "__dict__"):
        return None
    return value


def _row_to_dict(obj, include: list[str]) -> dict[str, Any]:
    return {k: _serialize(getattr(obj, k)) for k in include}


async def export_full(session: AsyncSession, owner_id: UUID) -> dict[str, Any]:
    """Return a JSON-serializable dict of the user's entire inventory."""
    # Items with related refs loaded
    items_stmt = (
        select(Item)
        .where(Item.owner_id == owner_id, Item.is_deleted.is_(False))
        .options(selectinload(Item.tags))
    )
    items = (await session.execute(items_stmt)).scalars().all()
    items_data = [
        {
            **_row_to_dict(
                i, ["id", "name", "description", "quantity", "min_quantity",
                     "notes", "is_favorite", "category_id", "location_id",
                     "warehouse_id", "image_id", "created_at", "updated_at"],
            ),
            "tag_names": [t.name for t in i.tags],
        }
        for i in items
    ]

    categories = (await session.execute(
        select(Category).where(Category.owner_id == owner_id)
    )).scalars().all()
    locations = (await session.execute(
        select(Location).where(Location.owner_id == owner_id)
    )).scalars().all()
    tags = (await session.execute(
        select(Tag).where(Tag.owner_id == owner_id)
    )).scalars().all()
    warehouses = (await session.execute(
        select(Warehouse).where(Warehouse.owner_id == owner_id)
    )).scalars().all()
    item_types = (await session.execute(
        select(ItemType).where(ItemType.owner_id == owner_id)
    )).scalars().all()
    custom_fields = (await session.execute(
        select(CustomField).where(CustomField.owner_id == owner_id)
    )).scalars().all()
    templates = (await session.execute(
        select(ItemTemplate).where(ItemTemplate.owner_id == owner_id)
    )).scalars().all()

    lists = (await session.execute(
        select(UserList).where(UserList.owner_id == owner_id)
        .options(selectinload(UserList.entries))
    )).scalars().all()
    lists_data = [
        {
            **_row_to_dict(
                lst, ["id", "kind", "title", "description", "start_date",
                       "end_date", "budget", "created_at", "updated_at"],
            ),
            "entries": [
                _row_to_dict(
                    e, ["id", "position", "name", "quantity", "note",
                         "price", "link", "is_done", "created_at"],
                ) for e in lst.entries
            ],
        }
        for lst in lists
    ]

    groups_owned = (await session.execute(
        select(Group).where(Group.owner_id == owner_id)
        .options(selectinload(Group.members))
    )).scalars().all()
    groups_data = [
        {
            **_row_to_dict(g, ["id", "name", "created_at"]),
            "member_user_ids": [str(m.user_id) for m in g.members],
        }
        for g in groups_owned
    ]

    return {
        "format_version": 1,
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "owner_id": str(owner_id),
        "items": items_data,
        "categories": [
            _row_to_dict(c, ["id", "name", "parent_id"]) for c in categories
        ],
        "locations": [
            _row_to_dict(loc, ["id", "floor", "room", "zone"]) for loc in locations
        ],
        "tags": [_row_to_dict(t, ["id", "name"]) for t in tags],
        "warehouses": [
            _row_to_dict(w, ["id", "name", "description", "created_at"])
            for w in warehouses
        ],
        "item_types": [
            _row_to_dict(t, ["id", "name", "icon"]) for t in item_types
        ],
        "custom_fields": [
            _row_to_dict(f, ["id", "name", "field_type"]) for f in custom_fields
        ],
        "item_templates": [
            {
                **_row_to_dict(t, ["id", "name", "created_at"]),
                "payload": t.payload,
            }
            for t in templates
        ],
        "lists": lists_data,
        "groups_owned": groups_data,
    }
