"""locations.sort_order + locations.floor_plan_image_id

Revision ID: 0014
Revises: 0013
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0014"
down_revision: Union[str, None] = "0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "locations",
        sa.Column(
            "sort_order", sa.Integer(), nullable=False, server_default="0",
        ),
    )
    op.add_column(
        "locations",
        sa.Column(
            "floor_plan_image_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("images.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("locations", "floor_plan_image_id")
    op.drop_column("locations", "sort_order")
