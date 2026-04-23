"""webhooks + webhook_deliveries

Revision ID: 0013
Revises: 0012
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0013"
down_revision: Union[str, None] = "0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "webhooks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "owner_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("secret", sa.String(200), nullable=True),
        sa.Column("events", postgresql.JSONB(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_fired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_status", sa.Integer(), nullable=True),
    )
    op.create_index("ix_webhooks_owner_id", "webhooks", ["owner_id"])

    op.create_table(
        "webhook_deliveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "webhook_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("webhooks.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("event", sa.String(60), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("response_excerpt", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_webhook_deliveries_webhook_id", "webhook_deliveries", ["webhook_id"])
    op.create_index("ix_webhook_deliveries_event", "webhook_deliveries", ["event"])
    op.create_index("ix_webhook_deliveries_created_at", "webhook_deliveries", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_webhook_deliveries_created_at", table_name="webhook_deliveries")
    op.drop_index("ix_webhook_deliveries_event", table_name="webhook_deliveries")
    op.drop_index("ix_webhook_deliveries_webhook_id", table_name="webhook_deliveries")
    op.drop_table("webhook_deliveries")
    op.drop_index("ix_webhooks_owner_id", table_name="webhooks")
    op.drop_table("webhooks")
