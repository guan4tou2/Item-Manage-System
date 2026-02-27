from alembic import op
import sqlalchemy as sa


revision = "20260220_000004"
down_revision = "20260119_002347"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("items") as batch_op:
        batch_op.add_column(sa.Column("visibility", sa.String(length=20), nullable=False, server_default="private"))
        batch_op.add_column(sa.Column("shared_with", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")))
        batch_op.create_index("ix_items_visibility", ["visibility"], unique=False)

    with op.batch_alter_table("travel_items") as batch_op:
        batch_op.add_column(sa.Column("list_scope", sa.String(length=20), nullable=False, server_default="common"))
        batch_op.add_column(sa.Column("assignee", sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column("visibility", sa.String(length=20), nullable=False, server_default="shared"))
        batch_op.create_index("ix_travel_items_list_scope", ["list_scope"], unique=False)
        batch_op.create_index("ix_travel_items_assignee", ["assignee"], unique=False)
        batch_op.create_index("ix_travel_items_visibility", ["visibility"], unique=False)

    with op.batch_alter_table("shopping_items") as batch_op:
        batch_op.add_column(sa.Column("list_scope", sa.String(length=20), nullable=False, server_default="common"))
        batch_op.add_column(sa.Column("assignee", sa.String(length=50), nullable=True))
        batch_op.create_index("ix_shopping_items_list_scope", ["list_scope"], unique=False)
        batch_op.create_index("ix_shopping_items_assignee", ["assignee"], unique=False)

    op.create_table(
        "line_user_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.String(length=50), nullable=False),
        sa.Column("line_user_id", sa.String(length=100), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_line_user_links_user_id", "line_user_links", ["user_id"], unique=False)
    op.create_index("ix_line_user_links_line_user_id", "line_user_links", ["line_user_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_line_user_links_line_user_id", table_name="line_user_links")
    op.drop_index("ix_line_user_links_user_id", table_name="line_user_links")
    op.drop_table("line_user_links")

    with op.batch_alter_table("shopping_items") as batch_op:
        batch_op.drop_index("ix_shopping_items_assignee")
        batch_op.drop_index("ix_shopping_items_list_scope")
        batch_op.drop_column("assignee")
        batch_op.drop_column("list_scope")

    with op.batch_alter_table("travel_items") as batch_op:
        batch_op.drop_index("ix_travel_items_visibility")
        batch_op.drop_index("ix_travel_items_assignee")
        batch_op.drop_index("ix_travel_items_list_scope")
        batch_op.drop_column("visibility")
        batch_op.drop_column("assignee")
        batch_op.drop_column("list_scope")

    with op.batch_alter_table("items") as batch_op:
        batch_op.drop_index("ix_items_visibility")
        batch_op.drop_column("shared_with")
        batch_op.drop_column("visibility")
