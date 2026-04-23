"""line + telegram links + web push subscriptions

Revision ID: 0011
Revises: 0010
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "line_user_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("line_user_id", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", name="uq_line_links_user"),
    )
    op.create_index("ix_line_user_links_user_id", "line_user_links", ["user_id"])
    op.create_index("ix_line_user_links_line_user_id", "line_user_links", ["line_user_id"])

    op.create_table(
        "telegram_user_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chat_id", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", name="uq_tg_links_user"),
    )
    op.create_index("ix_telegram_user_links_user_id", "telegram_user_links", ["user_id"])
    op.create_index("ix_telegram_user_links_chat_id", "telegram_user_links", ["chat_id"])

    op.create_table(
        "web_push_subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("endpoint", sa.Text(), nullable=False, unique=True),
        sa.Column("p256dh", sa.String(200), nullable=False),
        sa.Column("auth", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_web_push_subscriptions_user_id", "web_push_subscriptions", ["user_id"])
    op.create_index("ix_web_push_subscriptions_endpoint", "web_push_subscriptions", ["endpoint"])


def downgrade() -> None:
    op.drop_index("ix_web_push_subscriptions_endpoint", table_name="web_push_subscriptions")
    op.drop_index("ix_web_push_subscriptions_user_id", table_name="web_push_subscriptions")
    op.drop_table("web_push_subscriptions")
    op.drop_index("ix_telegram_user_links_chat_id", table_name="telegram_user_links")
    op.drop_index("ix_telegram_user_links_user_id", table_name="telegram_user_links")
    op.drop_table("telegram_user_links")
    op.drop_index("ix_line_user_links_line_user_id", table_name="line_user_links")
    op.drop_index("ix_line_user_links_user_id", table_name="line_user_links")
    op.drop_table("line_user_links")
