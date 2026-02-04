"""add safety stock threshold

Revision ID: 20260115_000001
Revises: 20260114_000001
Create Date: 2026-01-15 00:55:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260115_000001"
down_revision = "20260114_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("items") as batch_op:
        batch_op.add_column(sa.Column("SafetyStock", sa.Integer(), server_default="0", nullable=False))


def downgrade() -> None:
    with op.batch_alter_table("items") as batch_op:
        batch_op.drop_column("SafetyStock")
