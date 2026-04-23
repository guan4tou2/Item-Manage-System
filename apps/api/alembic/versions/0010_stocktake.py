"""stocktakes + stocktake_items

Revision ID: 0010
Revises: 0009
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "stocktakes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "owner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('open','completed','cancelled')",
            name="ck_stocktakes_status_valid",
        ),
    )
    op.create_index("ix_stocktakes_owner_id", "stocktakes", ["owner_id"])

    op.create_table(
        "stocktake_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "stocktake_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("stocktakes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("expected_quantity", sa.Integer(), nullable=False),
        sa.Column("actual_quantity", sa.Integer(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("scanned_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("stocktake_id", "item_id", name="uq_stocktake_items_st_item"),
    )
    op.create_index("ix_stocktake_items_stocktake_id", "stocktake_items", ["stocktake_id"])
    op.create_index("ix_stocktake_items_item_id", "stocktake_items", ["item_id"])


def downgrade() -> None:
    op.drop_index("ix_stocktake_items_item_id", table_name="stocktake_items")
    op.drop_index("ix_stocktake_items_stocktake_id", table_name="stocktake_items")
    op.drop_table("stocktake_items")
    op.drop_index("ix_stocktakes_owner_id", table_name="stocktakes")
    op.drop_table("stocktakes")
