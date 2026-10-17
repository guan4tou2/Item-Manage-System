"""items.cost（單價，Numeric(12,2)，nullable）

Revision ID: 0021
Revises: 0020

純加欄（可逆）：`items.cost`＋非負 check constraint。
幣別為帳號層級設定（`users.preferences.currency`），本表不存幣別、不做匯率換算。
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0021"
down_revision: Union[str, None] = "0020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("items", sa.Column("cost", sa.Numeric(12, 2), nullable=True))
    op.create_check_constraint(
        "ck_items_cost_nonneg", "items", "cost IS NULL OR cost >= 0"
    )


def downgrade() -> None:
    op.drop_constraint("ck_items_cost_nonneg", "items", type_="check")
    op.drop_column("items", "cost")
