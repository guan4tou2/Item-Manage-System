from __future__ import annotations
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.category import Category
from app.models.customization import CustomField, ItemCustomValue, ItemTemplate, ItemType
from app.models.group import Group
from app.models.item import Item
from app.models.item_batch import ItemBatch
from app.models.item_history import ItemVersion, QuantityLog
from app.models.list import List as UserList
from app.models.loan import ItemLoan
from app.models.location import Location
from app.models.notification_preference import NotificationPreference
from app.models.stocktake import Stocktake, StocktakeItem
from app.models.tag import Tag
from app.models.user import User
from app.models.warehouse import Warehouse
from app.models.webhook import Webhook
from app.schemas.preferences import currency_from_raw

#: 備份格式版本：新增可選欄位/實體 +1、破壞性變更 +1（匯入端相容矩陣見
#: `docs/plans/2026-10-17-phase29-backup-restore.md`）。
#: v1 → v2：locations 改樹欄位；v2 → v3：items.cost／lists.budget／entry.price；
#: v3 → v4（Phase 29）：items.barcode/track_batches＋批次／借還／歷程／盤點／
#: webhooks／通知偏好／幣別等全量實體。
FORMAT_VERSION = 4


def _serialize(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Decimal):
        # JSONResponse uses json.dumps: Decimal is not serializable.
        # Keep exact 2-dp strings (DB Numeric(12,2) scale) stable for backup.
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        # datetime is a date subclass, so this must come after the check above.
        # Plain date would otherwise fall through and crash json.dumps.
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
        .order_by(Item.created_at, Item.id)
    )
    items = (await session.execute(items_stmt)).scalars().all()
    items_data = [
        {
            **_row_to_dict(
                i, ["id", "name", "description", "barcode", "quantity", "min_quantity",
                     "cost", "track_batches",
                     "notes", "is_favorite", "category_id", "location_id",
                     "warehouse_id", "image_id", "created_at", "updated_at"],
            ),
            "tag_names": sorted(t.name for t in i.tags),
        }
        for i in items
    ]

    # Child rows are scoped to the exported (non-deleted) items.
    user_item_ids = select(Item.id).where(
        Item.owner_id == owner_id, Item.is_deleted.is_(False)
    )

    categories = (await session.execute(
        select(Category).where(Category.owner_id == owner_id)
        .order_by(Category.name, Category.id)
    )).scalars().all()
    locations = (await session.execute(
        select(Location).where(Location.owner_id == owner_id)
        .order_by(Location.name, Location.id)
    )).scalars().all()
    tags = (await session.execute(
        select(Tag).where(Tag.owner_id == owner_id)
        .order_by(Tag.name, Tag.id)
    )).scalars().all()
    warehouses = (await session.execute(
        select(Warehouse).where(Warehouse.owner_id == owner_id)
        .order_by(Warehouse.name, Warehouse.id)
    )).scalars().all()
    item_types = (await session.execute(
        select(ItemType).where(ItemType.owner_id == owner_id)
        .order_by(ItemType.name, ItemType.id)
    )).scalars().all()
    custom_fields = (await session.execute(
        select(CustomField).where(CustomField.owner_id == owner_id)
        .order_by(CustomField.name, CustomField.id)
    )).scalars().all()
    templates = (await session.execute(
        select(ItemTemplate).where(ItemTemplate.owner_id == owner_id)
        .order_by(ItemTemplate.name, ItemTemplate.id)
    )).scalars().all()

    custom_values = (await session.execute(
        select(ItemCustomValue)
        .where(ItemCustomValue.item_id.in_(user_item_ids))
        .order_by(ItemCustomValue.item_id, ItemCustomValue.custom_field_id)
    )).scalars().all()
    batches = (await session.execute(
        select(ItemBatch)
        .where(ItemBatch.item_id.in_(user_item_ids))
        .order_by(ItemBatch.created_at, ItemBatch.id)
    )).scalars().all()
    loans = (await session.execute(
        select(ItemLoan)
        .where(ItemLoan.item_id.in_(user_item_ids))
        .order_by(ItemLoan.created_at, ItemLoan.id)
    )).scalars().all()
    quantity_logs = (await session.execute(
        select(QuantityLog)
        .where(QuantityLog.item_id.in_(user_item_ids))
        .order_by(QuantityLog.created_at, QuantityLog.id)
    )).scalars().all()
    versions = (await session.execute(
        select(ItemVersion)
        .where(ItemVersion.item_id.in_(user_item_ids))
        .order_by(ItemVersion.created_at, ItemVersion.id)
    )).scalars().all()

    lists = (await session.execute(
        select(UserList).where(UserList.owner_id == owner_id)
        .options(selectinload(UserList.entries))
        .order_by(UserList.created_at, UserList.id)
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
                ) for e in sorted(lst.entries, key=lambda e: (e.position, str(e.id)))
            ],
        }
        for lst in lists
    ]

    stocktakes = (await session.execute(
        select(Stocktake).where(Stocktake.owner_id == owner_id)
        .order_by(Stocktake.started_at, Stocktake.id)
    )).scalars().all()
    stocktake_ids = [s.id for s in stocktakes]
    stocktake_items: list[StocktakeItem] = []
    if stocktake_ids:
        stocktake_items = list((await session.execute(
            select(StocktakeItem)
            .where(StocktakeItem.stocktake_id.in_(stocktake_ids))
            .order_by(StocktakeItem.stocktake_id, StocktakeItem.scanned_at, StocktakeItem.id)
        )).scalars().all())
    stocktake_items_by_stocktake: dict[UUID, list[StocktakeItem]] = {}
    for row in stocktake_items:
        stocktake_items_by_stocktake.setdefault(row.stocktake_id, []).append(row)
    stocktakes_data = [
        {
            **_row_to_dict(s, ["id", "name", "status", "started_at", "completed_at"]),
            "items": [
                _row_to_dict(
                    row,
                    ["item_id", "expected_quantity", "actual_quantity", "note", "scanned_at"],
                )
                for row in stocktake_items_by_stocktake.get(s.id, [])
            ],
        }
        for s in stocktakes
    ]

    webhooks = (await session.execute(
        select(Webhook).where(Webhook.owner_id == owner_id)
        .order_by(Webhook.created_at, Webhook.id)
    )).scalars().all()

    notification_preferences = (await session.execute(
        select(NotificationPreference)
        .where(NotificationPreference.user_id == owner_id)
        .order_by(NotificationPreference.type, NotificationPreference.channel)
    )).scalars().all()

    raw_preferences = (await session.execute(
        select(User.preferences).where(User.id == owner_id)
    )).scalar_one_or_none() or {}

    groups_owned = (await session.execute(
        select(Group).where(Group.owner_id == owner_id)
        .options(selectinload(Group.members))
        .order_by(Group.name, Group.id)
    )).scalars().all()
    groups_data = [
        {
            **_row_to_dict(g, ["id", "name", "created_at"]),
            "member_user_ids": sorted(str(m.user_id) for m in g.members),
        }
        for g in groups_owned
    ]

    return {
        "format_version": FORMAT_VERSION,
        "exported_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z",
        "owner_id": str(owner_id),
        "preferences": {"currency": currency_from_raw(raw_preferences)},
        "items": items_data,
        "categories": [
            _row_to_dict(c, ["id", "name", "parent_id"]) for c in categories
        ],
        "locations": [
            _row_to_dict(
                loc,
                ["id", "parent_id", "name", "kind", "sort_order", "floor_plan_image_id"],
            )
            for loc in locations
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
        "item_custom_values": [
            _row_to_dict(v, ["item_id", "custom_field_id", "value"])
            for v in custom_values
        ],
        "item_batches": [
            _row_to_dict(
                b,
                ["id", "item_id", "quantity", "expiry_date", "received_at",
                 "note", "is_depleted", "created_at"],
            )
            for b in batches
        ],
        "loans": [
            _row_to_dict(
                loan,
                ["id", "item_id", "borrower_user_id", "borrower_label", "lent_at",
                 "expected_return", "returned_at", "notes"],
            )
            for loan in loans
        ],
        "quantity_logs": [
            _row_to_dict(
                log,
                ["id", "item_id", "user_id", "old_quantity", "new_quantity",
                 "reason", "created_at"],
            )
            for log in quantity_logs
        ],
        "item_versions": [
            {
                **_row_to_dict(v, ["id", "item_id", "user_id", "created_at"]),
                "snapshot": v.snapshot,
            }
            for v in versions
        ],
        "lists": lists_data,
        "stocktakes": stocktakes_data,
        "webhooks": [
            _row_to_dict(
                w,
                ["id", "name", "url", "secret", "events", "is_active", "created_at"],
            )
            for w in webhooks
        ],
        "notification_preferences": [
            _row_to_dict(p, ["type", "channel", "enabled"])
            for p in notification_preferences
        ],
        "groups_owned": groups_data,
    }
