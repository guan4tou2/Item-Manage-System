"""ai_draft_items ＋ ai_usage（Phase 32 AI 批次入庫）

Revision ID: 0024
Revises: 0023

- `ai_draft_items`：每張上傳照片一列草稿；狀態機
  `pending → processing → ready | failed`（終態 `accepted | discarded`）；
  `payload` 為 version=1 建議快照；`item_id` 記錄接受後建立的物品。
- `ai_usage`：per-user 每日 LLM 配額計數（`day` 為 Asia/Taipei 當地日期）。
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0024"
down_revision: Union[str, None] = "0023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_draft_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "owner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column(
            "image_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("images.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "status", sa.String(length=20), nullable=False, server_default="pending"
        ),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("error_code", sa.String(length=32), nullable=True),
        sa.Column(
            "item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("items.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "source IN ('batch_photo', 'receipt')",
            name="ck_ai_draft_items_source",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'ready', 'failed', 'accepted', 'discarded')",
            name="ck_ai_draft_items_status",
        ),
    )
    op.create_index(
        "ix_ai_draft_items_owner_status",
        "ai_draft_items",
        ["owner_id", "status"],
    )

    op.create_table(
        "ai_usage",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("calls", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("user_id", "day", name="uq_ai_usage_user_day"),
    )


def downgrade() -> None:
    op.drop_table("ai_usage")
    op.drop_index("ix_ai_draft_items_owner_status", table_name="ai_draft_items")
    op.drop_table("ai_draft_items")
