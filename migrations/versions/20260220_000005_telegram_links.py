from alembic import op
import sqlalchemy as sa


revision = "20260220_000005"
down_revision = "20260220_000004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "telegram_user_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.String(length=50), nullable=False),
        sa.Column("telegram_user_id", sa.String(length=100), nullable=False, unique=True),
        sa.Column("chat_id", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_telegram_user_links_user_id", "telegram_user_links", ["user_id"], unique=False)
    op.create_index("ix_telegram_user_links_telegram_user_id", "telegram_user_links", ["telegram_user_id"], unique=True)
    op.create_index("ix_telegram_user_links_chat_id", "telegram_user_links", ["chat_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_telegram_user_links_chat_id", table_name="telegram_user_links")
    op.drop_index("ix_telegram_user_links_telegram_user_id", table_name="telegram_user_links")
    op.drop_index("ix_telegram_user_links_user_id", table_name="telegram_user_links")
    op.drop_table("telegram_user_links")
