"""webhook_deliveries.attempt + webhook_deliveries.next_retry_at

Revision ID: 0015
Revises: 0014
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0015"
down_revision: Union[str, None] = "0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "webhook_deliveries",
        sa.Column(
            "attempt", sa.Integer(), nullable=False, server_default="1",
        ),
    )
    op.add_column(
        "webhook_deliveries",
        sa.Column(
            "next_retry_at", sa.DateTime(timezone=True), nullable=True,
        ),
    )
    op.create_index(
        "ix_webhook_deliveries_next_retry_at",
        "webhook_deliveries",
        ["next_retry_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_webhook_deliveries_next_retry_at", table_name="webhook_deliveries")
    op.drop_column("webhook_deliveries", "next_retry_at")
    op.drop_column("webhook_deliveries", "attempt")
