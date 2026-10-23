"""reports.kind＋period 放寬（Phase 42 週報）

Revision ID: 0026
Revises: 0025

- `reports.period`：varchar(7) → varchar(10)，容納 ISO 週 key（如 `2026-W42`）
- 新增 `reports.kind`：`monthly`（預設）／`weekly`；既有列自動為 monthly
- `UNIQUE(user_id, period)` 不變；兩種 key 格式不重疊

Downgrade 會先刪除週報列（`kind='weekly'`）再縮回 varchar(7)，
因為週報 key 放不進舊長度；此為 destructive 操作，文件已註明。
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0026"
down_revision: Union[str, None] = "0025"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("reports") as batch:
        batch.alter_column(
            "period",
            existing_type=sa.String(length=7),
            type_=sa.String(length=10),
            existing_nullable=False,
        )
        batch.add_column(
            sa.Column(
                "kind",
                sa.String(length=8),
                nullable=False,
                server_default="monthly",
            )
        )


def downgrade() -> None:
    op.execute("DELETE FROM reports WHERE kind = 'weekly'")
    with op.batch_alter_table("reports") as batch:
        batch.drop_column("kind")
        batch.alter_column(
            "period",
            existing_type=sa.String(length=10),
            type_=sa.String(length=7),
            existing_nullable=False,
        )
