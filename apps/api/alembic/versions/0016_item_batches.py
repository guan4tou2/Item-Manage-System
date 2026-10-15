"""item_batches + items.track_batches

Revision ID: 0016
Revises: 0015
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0016"
down_revision: Union[str, None] = "0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "item_batches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("received_at", sa.Date(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "is_depleted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
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
            "quantity >= 0", name="ck_item_batches_quantity_nonneg"
        ),
    )
    op.create_index("ix_item_batches_item_id", "item_batches", ["item_id"])
    op.create_index(
        "ix_item_batches_item_depleted", "item_batches", ["item_id", "is_depleted"]
    )
    op.create_index(
        "ix_item_batches_expiry_date", "item_batches", ["expiry_date"]
    )

    op.add_column(
        "items",
        sa.Column(
            "track_batches",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("items", "track_batches")
    op.drop_index("ix_item_batches_expiry_date", table_name="item_batches")
    op.drop_index("ix_item_batches_item_depleted", table_name="item_batches")
    op.drop_index("ix_item_batches_item_id", table_name="item_batches")
    op.drop_table("item_batches")
