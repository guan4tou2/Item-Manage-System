"""locations 樹化（平面 floor/room/zone → 任意深度樹）

Revision ID: 0020
Revises: 0019

破壞性遷移（不可逆）：
1. 加 `parent_id`／`name`／`kind`；放寬 `floor` NOT NULL（遷移期間新列不填舊欄）
2. 執行 `location_tree_migration.migrate_flat()`：建立 canonical 節點、物品重新指向、
   刪除舊列（報告寫入 alembic log）
3. `name` NOT NULL；移除 `floor`／`room`／`zone`
4. 索引（owner+parent+sort、同 parent 同名 partial unique ×2）＋ self-FK（RESTRICT）
"""
from __future__ import annotations

import logging
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.services.location_tree_migration import migrate_flat, preview_paths

revision: str = "0020"
down_revision: Union[str, None] = "0019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

logger = logging.getLogger("alembic.runtime.migration")


def upgrade() -> None:
    op.add_column("locations", sa.Column("parent_id", sa.Integer(), nullable=True))
    op.add_column("locations", sa.Column("name", sa.String(length=50), nullable=True))
    op.add_column("locations", sa.Column("kind", sa.String(length=20), nullable=True))
    op.alter_column("locations", "floor", existing_type=sa.String(length=50), nullable=True)

    bind = op.get_bind()
    planned = preview_paths(bind)
    report = migrate_flat(bind)
    logger.info("location tree planned paths: %s", planned)
    logger.info("location tree migration report: %s", report.as_dict())

    op.alter_column("locations", "name", existing_type=sa.String(length=50), nullable=False)
    op.drop_column("locations", "zone")
    op.drop_column("locations", "room")
    op.drop_column("locations", "floor")

    op.create_index(
        "ix_locations_owner_parent_sort",
        "locations",
        ["owner_id", "parent_id", "sort_order"],
    )
    op.create_index(
        "uq_locations_owner_root_name",
        "locations",
        ["owner_id", "name"],
        unique=True,
        postgresql_where=sa.text("parent_id IS NULL"),
    )
    op.create_index(
        "uq_locations_owner_parent_name",
        "locations",
        ["owner_id", "parent_id", "name"],
        unique=True,
        postgresql_where=sa.text("parent_id IS NOT NULL"),
    )
    op.create_foreign_key(
        "fk_locations_parent_id_self",
        "locations",
        "locations",
        ["parent_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    raise RuntimeError(
        "Phase 26 位置樹遷移不可逆：樹結構無法還原為 floor/room/zone 三欄"
    )
