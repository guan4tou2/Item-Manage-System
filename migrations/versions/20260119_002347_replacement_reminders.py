"""add replacement reminder settings

Revision ID: 20260119_002347
Revises: 20260117_000003_travel_and_shopping
Create Date: 2026-01-19 00:23:47
"""

from alembic import op
import sqlalchemy as sa


revision = "20260119_002347"
down_revision = "20260117_000003_travel_and_shopping"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("replacement_enabled", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch_op.add_column(sa.Column("replacement_intervals", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")))


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("replacement_intervals")
        batch_op.drop_column("replacement_enabled")
