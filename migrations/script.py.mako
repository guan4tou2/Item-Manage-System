"""Mako template for new revision files.

${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlparse


def upgrade() -> None:
    """Upgrade database."""
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """Downgrade database."""
    ${downgrades if downgrades else "pass"}


def process_revision_script(
    directives: list[Union[sa.schema.CreateTable, sa.schema.AlterTable]],
) -> list[Union[sa.schema.CreateTable, sa.schema.AlterTable]]:
    """This function processes the generated migration script directives.

    It formats the SQL statements using sqlparse to make them more readable.
    """
    if directives and "postgresql" == context.config.get_main_option("sqlalchemy.url").startswith(
        "postgresql"
    ):
        from alembic.runtime.migration import MigrationContext

        migration_context = MigrationContext.configure(dialect_name="postgresql")

        for directive in directives:
            if isinstance(directive, (sa.schema.CreateTable, sa.schema.AlterTable)):
                for sql_statement in directive.to_sql(migration_context.connection.dialect):
                    sql = sqlparse.format(sql_statement, reindent=True)
                    directive.to_sql = lambda: sql

    return directives
