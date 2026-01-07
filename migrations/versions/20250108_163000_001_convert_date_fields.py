"""Convert date fields from String to Date type

Revision ID: 001
Revises:
Create Date: 2025-01-08 16:30:00
"""
from typing import Sequence, Union
from datetime import date

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    """Convert WarrantyExpiry and UsageExpiry from String to Date."""
    # Step 1: Add temporary Date columns
    op.add_column('items', sa.Column('_warranty_expiry_date', sa.Date(), nullable=True))
    op.add_column('items', sa.Column('_usage_expiry_date', sa.Date(), nullable=True))

    # Step 2: Copy data from String to Date
    op.execute("""
        UPDATE items
        SET _warranty_expiry_date = CASE
            WHEN WarrantyExpiry IS NOT NULL AND WarrantyExpiry != '' THEN WarrantyExpiry::date
            ELSE NULL
        END
    """)

    op.execute("""
        UPDATE items
        SET _usage_expiry_date = CASE
            WHEN UsageExpiry IS NOT NULL AND UsageExpiry != '' THEN UsageExpiry::date
            ELSE NULL
        END
    """)

    # Step 3: Drop old String columns
    op.drop_column('items', 'WarrantyExpiry')
    op.drop_column('items', 'UsageExpiry')

    # Step 4: Rename temporary columns to original names
    op.alter_column('items', '_warranty_expiry_date', new_column_name='WarrantyExpiry')
    op.alter_column('items', '_usage_expiry_date', new_column_name='UsageExpiry')


def downgrade() -> None:
    """Revert WarrantyExpiry and UsageExpiry back to String."""
    # Step 1: Add temporary String columns
    op.add_column('items', sa.Column('_warranty_expiry_str', sa.String(20), nullable=True))
    op.add_column('items', sa.Column('_usage_expiry_str', sa.String(20), nullable=True))

    # Step 2: Copy data from Date to String
    op.execute("""
        UPDATE items
        SET _warranty_expiry_str = WarrantyExpiry::text
        WHERE WarrantyExpiry IS NOT NULL
    """)

    op.execute("""
        UPDATE items
        SET _usage_expiry_str = UsageExpiry::text
        WHERE UsageExpiry IS NOT NULL
    """)

    # Step 3: Drop Date columns
    op.drop_column('items', 'WarrantyExpiry')
    op.drop_column('items', 'UsageExpiry')

    # Step 4: Rename temporary columns to original names
    op.alter_column('items', '_warranty_expiry_str', new_column_name='WarrantyExpiry')
    op.alter_column('items', '_usage_expiry_str', new_column_name='UsageExpiry')
