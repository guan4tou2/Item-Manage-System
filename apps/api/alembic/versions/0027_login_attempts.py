"""login_attempts（Phase 43 登入防暴力破解）

Revision ID: 0027
Revises: 0026

每次登入失敗寫入 account／ip 兩列；key_hash 為 HMAC-SHA256，不保存原始
使用者名稱或 IP。此表只保存最近 24 小時的節流紀錄，downgrade 直接刪表。
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0027"
down_revision: Union[str, None] = "0026"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "login_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("kind", sa.String(length=8), nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_login_attempts_lookup",
        "login_attempts",
        ["kind", "key_hash", "created_at"],
    )
    op.create_index(
        "ix_login_attempts_created_at",
        "login_attempts",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_login_attempts_created_at", table_name="login_attempts")
    op.drop_index("ix_login_attempts_lookup", table_name="login_attempts")
    op.drop_table("login_attempts")
