"""users.token_version（Phase 44 session 撤銷）

Revision ID: 0028
Revises: 0027

access／refresh token 帶 `ver` claim，驗證時與此欄比對；改密碼或
「登出所有裝置」時遞增即可讓既有 token 全部失效。既有列以
server_default 0 回填，與沒有 `ver` 的舊 token（視為 0）相容。
downgrade 直接刪欄（版本計數只影響 session 有效性，不含使用者資料）。
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0028"
down_revision: Union[str, None] = "0027"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "token_version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "token_version")
