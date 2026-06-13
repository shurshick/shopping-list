"""ops admin fields

Revision ID: 20260613_0004
Revises: 20260613_0003
Create Date: 2026-06-13
"""

from alembic import op
import sqlalchemy as sa


revision = "20260613_0004"
down_revision = "20260613_0003"
branch_labels = None
depends_on = None


def table_exists(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)


def column_exists(table_name: str, column_name: str) -> bool:
    if not table_exists(table_name):
        return False
    return any(column["name"] == column_name for column in sa.inspect(op.get_bind()).get_columns(table_name))


def upgrade() -> None:
    if not column_exists("users", "is_active"):
        op.add_column("users", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
    if not column_exists("users", "last_login_at"):
        op.add_column("users", sa.Column("last_login_at", sa.DateTime(), nullable=True))
    if not column_exists("shopping_lists", "archived_at"):
        op.add_column("shopping_lists", sa.Column("archived_at", sa.DateTime(), nullable=True))
        op.create_index(op.f("ix_shopping_lists_archived_at"), "shopping_lists", ["archived_at"], unique=False)
    if not column_exists("list_invites", "revoked_at"):
        op.add_column("list_invites", sa.Column("revoked_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    if column_exists("list_invites", "revoked_at"):
        op.drop_column("list_invites", "revoked_at")
    if column_exists("shopping_lists", "archived_at"):
        op.drop_index(op.f("ix_shopping_lists_archived_at"), table_name="shopping_lists")
        op.drop_column("shopping_lists", "archived_at")
    if column_exists("users", "last_login_at"):
        op.drop_column("users", "last_login_at")
    if column_exists("users", "is_active"):
        op.drop_column("users", "is_active")
