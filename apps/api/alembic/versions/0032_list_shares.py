"""清單分享唯讀憑證。

Revision ID: 0032
Revises: 0031
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0032"
down_revision = "0031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "list_shares",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "list_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("lists.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "owner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.CHAR(64), nullable=False, unique=True),
        sa.Column("token_prefix", sa.String(6), nullable=False),
        sa.Column(
            "show_prices", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_accessed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("access_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_list_shares_list_id", "list_shares", ["list_id"])


def downgrade() -> None:
    op.drop_index("ix_list_shares_list_id", table_name="list_shares")
    op.drop_table("list_shares")
