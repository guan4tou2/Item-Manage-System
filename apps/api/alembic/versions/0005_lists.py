"""lists + list_entries

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-23 00:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "lists",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "owner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("budget", sa.Numeric(12, 2), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "kind IN ('travel','shopping','collection','generic')",
            name="ck_lists_kind_valid",
        ),
        sa.CheckConstraint(
            "budget IS NULL OR budget >= 0", name="ck_lists_budget_nonneg"
        ),
        sa.CheckConstraint(
            "start_date IS NULL OR end_date IS NULL OR end_date >= start_date",
            name="ck_lists_date_order",
        ),
    )
    op.create_index("ix_lists_owner_id", "lists", ["owner_id"])

    op.create_table(
        "list_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "list_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("lists.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("price", sa.Numeric(12, 2), nullable=True),
        sa.Column("link", sa.String(length=500), nullable=True),
        sa.Column(
            "is_done", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "position >= 0", name="ck_list_entries_position_nonneg"
        ),
        sa.CheckConstraint(
            "quantity IS NULL OR quantity >= 1",
            name="ck_list_entries_quantity_positive",
        ),
        sa.CheckConstraint(
            "price IS NULL OR price >= 0", name="ck_list_entries_price_nonneg"
        ),
    )
    op.create_index(
        "ix_list_entries_list_id_position",
        "list_entries",
        ["list_id", "position"],
    )


def downgrade() -> None:
    op.drop_index("ix_list_entries_list_id_position", table_name="list_entries")
    op.drop_table("list_entries")
    op.drop_index("ix_lists_owner_id", table_name="lists")
    op.drop_table("lists")
