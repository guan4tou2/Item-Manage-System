"""warehouses + items.warehouse_id

Revision ID: 0012
Revises: 0011
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0012"
down_revision: Union[str, None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "warehouses",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "owner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            nullable=False, server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("owner_id", "name", name="uq_warehouses_owner_name"),
    )
    op.create_index("ix_warehouses_owner_id", "warehouses", ["owner_id"])

    op.add_column(
        "items",
        sa.Column(
            "warehouse_id",
            sa.Integer(),
            sa.ForeignKey("warehouses.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_items_warehouse_id", "items", ["warehouse_id"])


def downgrade() -> None:
    op.drop_index("ix_items_warehouse_id", table_name="items")
    op.drop_column("items", "warehouse_id")
    op.drop_index("ix_warehouses_owner_id", table_name="warehouses")
    op.drop_table("warehouses")
