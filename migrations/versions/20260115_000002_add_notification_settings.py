"""add notification channels and ladder

Revision ID: 20260115_000002
Revises: 20260115_000001
Create Date: 2026-01-15 01:10:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260115_000002"
down_revision = "20260115_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("notify_channels", sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False))
        batch_op.add_column(sa.Column("reminder_ladder", sa.String(50), server_default="30,14,7,3,1", nullable=False))


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("reminder_ladder")
        batch_op.drop_column("notify_channels")
