"""ai_draft_items.receipt_id（Phase 33 AI 收據辨識）

Revision ID: 0025
Revises: 0024

- `receipt_id`：同一次收據的多個品項草稿共用一個群組鍵（**無 FK**；群組沒有
  獨立生命週期，全部品項進入終態後自然消失）
- 索引 `(owner_id, receipt_id)`：佇列分組查詢用
- 既有列為 `NULL`（一般照片草稿），不需資料回填
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0025"
down_revision: Union[str, None] = "0024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ai_draft_items",
        sa.Column("receipt_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        "ix_ai_draft_items_owner_receipt",
        "ai_draft_items",
        ["owner_id", "receipt_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_ai_draft_items_owner_receipt", table_name="ai_draft_items")
    op.drop_column("ai_draft_items", "receipt_id")
