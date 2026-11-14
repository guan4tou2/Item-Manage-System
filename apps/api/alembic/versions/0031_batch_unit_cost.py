"""批次單位成本。

Revision ID: 0031
Revises: 0030
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0031"
down_revision = "0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "item_batches", sa.Column("unit_cost", sa.Numeric(12, 2), nullable=True)
    )
    op.create_check_constraint(
        "ck_item_batches_unit_cost_nonneg",
        "item_batches",
        "unit_cost IS NULL OR unit_cost >= 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_item_batches_unit_cost_nonneg", "item_batches", type_="check"
    )
    op.drop_column("item_batches", "unit_cost")
