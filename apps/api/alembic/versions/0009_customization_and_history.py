"""item_types + custom_fields + item_templates + item_history

Revision ID: 0009
Revises: 0008
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "item_types",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "owner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("icon", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("owner_id", "name", name="uq_item_types_owner_name"),
    )
    op.create_index("ix_item_types_owner_id", "item_types", ["owner_id"])

    op.create_table(
        "custom_fields",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "owner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("field_type", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("owner_id", "name", name="uq_custom_fields_owner_name"),
        sa.CheckConstraint(
            "field_type IN ('text','number','date','bool')",
            name="ck_custom_fields_type_valid",
        ),
    )
    op.create_index("ix_custom_fields_owner_id", "custom_fields", ["owner_id"])

    op.create_table(
        "item_custom_values",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "custom_field_id",
            sa.Integer(),
            sa.ForeignKey("custom_fields.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("value", postgresql.JSONB(), nullable=True),
        sa.UniqueConstraint("item_id", "custom_field_id", name="uq_icv_item_field"),
    )
    op.create_index("ix_item_custom_values_item_id", "item_custom_values", ["item_id"])
    op.create_index("ix_item_custom_values_custom_field_id", "item_custom_values", ["custom_field_id"])

    op.create_table(
        "item_templates",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "owner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("owner_id", "name", name="uq_item_templates_owner_name"),
    )
    op.create_index("ix_item_templates_owner_id", "item_templates", ["owner_id"])

    op.create_table(
        "quantity_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("old_quantity", sa.Integer(), nullable=False),
        sa.Column("new_quantity", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_quantity_logs_item_id", "quantity_logs", ["item_id"])
    op.create_index("ix_quantity_logs_created_at", "quantity_logs", ["created_at"])

    op.create_table(
        "item_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_item_versions_item_id", "item_versions", ["item_id"])
    op.create_index("ix_item_versions_created_at", "item_versions", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_item_versions_created_at", table_name="item_versions")
    op.drop_index("ix_item_versions_item_id", table_name="item_versions")
    op.drop_table("item_versions")
    op.drop_index("ix_quantity_logs_created_at", table_name="quantity_logs")
    op.drop_index("ix_quantity_logs_item_id", table_name="quantity_logs")
    op.drop_table("quantity_logs")
    op.drop_index("ix_item_templates_owner_id", table_name="item_templates")
    op.drop_table("item_templates")
    op.drop_index("ix_item_custom_values_custom_field_id", table_name="item_custom_values")
    op.drop_index("ix_item_custom_values_item_id", table_name="item_custom_values")
    op.drop_table("item_custom_values")
    op.drop_index("ix_custom_fields_owner_id", table_name="custom_fields")
    op.drop_table("custom_fields")
    op.drop_index("ix_item_types_owner_id", table_name="item_types")
    op.drop_table("item_types")
