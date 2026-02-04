from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260117_000003_travel_and_shopping"
down_revision = "20260115_000002_add_notification_settings"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("items", sa.Column("size_notes", postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default=sa.text("'{}'")))

    op.create_table(
        "travels",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False, index=True),
        sa.Column("owner", sa.String(length=50), nullable=True, index=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("shared", postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "travel_groups",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("travel_id", sa.Integer(), sa.ForeignKey("travels.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )

    op.create_table(
        "travel_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("travel_id", sa.Integer(), sa.ForeignKey("travels.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("group_id", sa.Integer(), sa.ForeignKey("travel_groups.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("source_type", sa.String(length=20), nullable=False, server_default="temp"),
        sa.Column("source_ref", sa.String(length=50), nullable=True, index=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("qty_required", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("qty_packed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("carried", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("size_notes", postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default=sa.text("'{}'")),
        sa.Column("is_temp", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "shopping_lists",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("list_type", sa.String(length=20), nullable=False, server_default="general"),
        sa.Column("travel_id", sa.Integer(), sa.ForeignKey("travels.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("owner", sa.String(length=50), nullable=True, index=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("shared", postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "shopping_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("list_id", sa.Integer(), sa.ForeignKey("shopping_lists.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("qty", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("budget", sa.Numeric(10, 2), nullable=True),
        sa.Column("price", sa.Numeric(10, 2), nullable=True),
        sa.Column("store", sa.String(length=120), nullable=True),
        sa.Column("link", sa.String(length=255), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("size_notes", postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default=sa.text("'{}'")),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="todo"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table("shopping_items")
    op.drop_table("shopping_lists")
    op.drop_table("travel_items")
    op.drop_table("travel_groups")
    op.drop_table("travels")
    op.drop_column("items", "size_notes")
