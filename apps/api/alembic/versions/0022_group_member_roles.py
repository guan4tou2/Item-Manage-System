"""group_members.role（admin | editor | viewer）

Revision ID: 0022
Revises: 0021

成員角色細化（Phase 30）：`group_members.role`＋CHECK＋既有列 backfill `editor`。
`owner` 不落庫——唯一事實來源維持 `groups.owner_id`（權限檢查先判 owner 再判 role）。
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0022"
down_revision: Union[str, None] = "0021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "group_members",
        sa.Column("role", sa.String(16), nullable=False, server_default="editor"),
    )
    op.create_check_constraint(
        "ck_group_members_role", "group_members", "role IN ('admin', 'editor', 'viewer')"
    )


def downgrade() -> None:
    op.drop_constraint("ck_group_members_role", "group_members", type_="check")
    op.drop_column("group_members", "role")
