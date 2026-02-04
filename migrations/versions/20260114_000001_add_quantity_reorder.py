"""add quantity and reorder level to items

Revision ID: 20260114_000001
Revises: 20250108_163000_001_convert_date_fields
Create Date: 2026-01-14 00:00:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260114_000001"
down_revision = "20250108_163000_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("items") as batch_op:
        batch_op.add_column(sa.Column("Quantity", sa.Integer(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("ReorderLevel", sa.Integer(), server_default="0", nullable=False))


def downgrade() -> None:
    with op.batch_alter_table("items") as batch_op:
        batch_op.drop_column("ReorderLevel")
        batch_op.drop_column("Quantity")
