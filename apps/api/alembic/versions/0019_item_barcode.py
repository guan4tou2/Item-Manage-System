"""items.barcode + barcode_lookups

Revision ID: 0019
Revises: 0018
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0019"
down_revision: Union[str, None] = "0018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("items", sa.Column("barcode", sa.String(length=32), nullable=True))
    op.create_index("ix_items_owner_barcode", "items", ["owner_id", "barcode"])

    op.create_table(
        "barcode_lookups",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=True),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("code", name="uq_barcode_lookups_code"),
    )


def downgrade() -> None:
    op.drop_table("barcode_lookups")
    op.drop_index("ix_items_owner_barcode", table_name="items")
    op.drop_column("items", "barcode")
