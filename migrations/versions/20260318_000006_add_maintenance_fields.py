"""add maintenance fields to items table

Revision ID: 20260318_000006
Revises: 20260220_000005
"""
from alembic import op
import sqlalchemy as sa


revision = "20260318_000006"
down_revision = "20260220_000005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("items") as batch_op:
        batch_op.add_column(
            sa.Column("MaintenanceCategory", sa.String(50), nullable=True, server_default="")
        )
        batch_op.add_column(
            sa.Column("MaintenanceIntervalDays", sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("LastMaintenanceDate", sa.Date(), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("items") as batch_op:
        batch_op.drop_column("LastMaintenanceDate")
        batch_op.drop_column("MaintenanceIntervalDays")
        batch_op.drop_column("MaintenanceCategory")
