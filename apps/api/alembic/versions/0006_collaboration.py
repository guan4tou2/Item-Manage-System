"""groups + group_members + item_loans + item_transfers

Revision ID: 0006
Revises: 0005
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "groups",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("owner_id", "name", name="uq_groups_owner_name"),
    )
    op.create_index("ix_groups_owner_id", "groups", ["owner_id"])

    op.create_table(
        "group_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("group_id", "user_id", name="uq_group_members_group_user"),
    )
    op.create_index("ix_group_members_group_id", "group_members", ["group_id"])
    op.create_index("ix_group_members_user_id", "group_members", ["user_id"])

    op.create_table(
        "item_loans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("borrower_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("borrower_label", sa.String(200), nullable=True),
        sa.Column("lent_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expected_return", sa.Date(), nullable=True),
        sa.Column("returned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "borrower_user_id IS NOT NULL OR borrower_label IS NOT NULL",
            name="ck_loans_borrower_presence",
        ),
    )
    op.create_index("ix_item_loans_item_id", "item_loans", ["item_id"])
    op.create_index("ix_item_loans_borrower_user_id", "item_loans", ["borrower_user_id"])
    op.create_index("ix_item_loans_returned_at", "item_loans", ["returned_at"])
    op.create_index(
        "uq_item_loans_one_active", "item_loans", ["item_id"],
        unique=True, postgresql_where=sa.text("returned_at IS NULL"),
        sqlite_where=sa.text("returned_at IS NULL"),
    )

    op.create_table(
        "item_transfers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("from_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("to_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending','accepted','rejected','cancelled')",
            name="ck_transfers_status_valid",
        ),
    )
    op.create_index("ix_item_transfers_item_id", "item_transfers", ["item_id"])
    op.create_index("ix_item_transfers_from_user_id", "item_transfers", ["from_user_id"])
    op.create_index("ix_item_transfers_to_user_id", "item_transfers", ["to_user_id"])
    op.create_index(
        "uq_item_transfers_one_pending", "item_transfers", ["item_id"],
        unique=True, postgresql_where=sa.text("status = 'pending'"),
        sqlite_where=sa.text("status = 'pending'"),
    )


def downgrade() -> None:
    op.drop_index("uq_item_transfers_one_pending", table_name="item_transfers")
    op.drop_index("ix_item_transfers_to_user_id", table_name="item_transfers")
    op.drop_index("ix_item_transfers_from_user_id", table_name="item_transfers")
    op.drop_index("ix_item_transfers_item_id", table_name="item_transfers")
    op.drop_table("item_transfers")
    op.drop_index("uq_item_loans_one_active", table_name="item_loans")
    op.drop_index("ix_item_loans_returned_at", table_name="item_loans")
    op.drop_index("ix_item_loans_borrower_user_id", table_name="item_loans")
    op.drop_index("ix_item_loans_item_id", table_name="item_loans")
    op.drop_table("item_loans")
    op.drop_index("ix_group_members_user_id", table_name="group_members")
    op.drop_index("ix_group_members_group_id", table_name="group_members")
    op.drop_table("group_members")
    op.drop_index("ix_groups_owner_id", table_name="groups")
    op.drop_table("groups")
