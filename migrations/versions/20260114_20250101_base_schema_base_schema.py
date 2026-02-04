"""Base schema

Revision ID: 20250101_base_schema
Revises: None
Create Date: 2026-01-14 20:21:38.669385+08:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20250101_base_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("User", sa.String(50), nullable=False, unique=True, index=True),
        sa.Column("Password", sa.String(255), nullable=False),
        sa.Column("admin", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("email", sa.String(255), server_default="", nullable=False),
        sa.Column("notify_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("notify_days", sa.Integer(), server_default="30", nullable=False),
        sa.Column("notify_time", sa.String(10), server_default="09:00", nullable=False),
        sa.Column("last_notification_date", sa.String(20), server_default="", nullable=False),
        sa.Column("password_changed", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("failed_attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("locked_until", sa.String(50), server_default="", nullable=False),
        sa.Column("last_login", sa.String(50), server_default="", nullable=False),
        sa.Column("last_login_ip", sa.String(100), server_default="", nullable=False),
        sa.Column("login_history", sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False),
    )

    op.create_table(
        "items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ItemID", sa.String(50), nullable=False, unique=True),
        sa.Column("ItemName", sa.String(100), nullable=False),
        sa.Column("ItemDesc", sa.Text()),
        sa.Column("ItemPic", sa.String(255), server_default=""),
        sa.Column("ItemThumb", sa.String(255), server_default=""),
        sa.Column("ItemPics", sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False),
        sa.Column("ItemStorePlace", sa.String(255), server_default=""),
        sa.Column("ItemType", sa.String(50)),
        sa.Column("ItemOwner", sa.String(50)),
        sa.Column("ItemGetDate", sa.String(20)),
        sa.Column("ItemFloor", sa.String(50)),
        sa.Column("ItemRoom", sa.String(50)),
        sa.Column("ItemZone", sa.String(50)),
        sa.Column("WarrantyExpiry", sa.String(20)),
        sa.Column("UsageExpiry", sa.String(20)),
        sa.Column("move_history", sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False),
        sa.Column("favorites", sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False),
        sa.Column("related_items", sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False),
        sa.Index("ix_items_ItemID", "ItemID"),
        sa.Index("ix_items_ItemName", "ItemName"),
        sa.Index("ix_items_ItemFloor", "ItemFloor"),
        sa.Index("ix_items_ItemRoom", "ItemRoom"),
        sa.Index("ix_items_ItemZone", "ItemZone"),
        sa.Index("ix_items_WarrantyExpiry", "WarrantyExpiry"),
        sa.Index("ix_items_UsageExpiry", "UsageExpiry"),
    )

    op.create_table(
        "item_types",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(50), nullable=False, unique=True),
        sa.Index("ix_item_types_name", "name"),
    )

    op.create_table(
        "logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("user", sa.String(50), nullable=False),
        sa.Column("item_id", sa.String(50)),
        sa.Column("item_name", sa.String(100)),
        sa.Column("details", sa.JSON()),
        sa.Column("timestamp", sa.String(50), server_default="", nullable=False),
        sa.Index("ix_logs_action", "action"),
        sa.Index("ix_logs_user", "user"),
        sa.Index("ix_logs_item_id", "item_id"),
        sa.Index("ix_logs_timestamp", "timestamp"),
    )

    op.create_table(
        "locations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("floor", sa.String(50)),
        sa.Column("room", sa.String(50)),
        sa.Column("zone", sa.String(50)),
        sa.Column("order", sa.Integer(), server_default="0", nullable=False),
        sa.Index("ix_locations_floor", "floor"),
        sa.Index("ix_locations_room", "room"),
        sa.Index("ix_locations_zone", "zone"),
    )


def downgrade() -> None:
    op.drop_table("locations")
    op.drop_table("logs")
    op.drop_table("item_types")
    op.drop_table("items")
    op.drop_table("users")
