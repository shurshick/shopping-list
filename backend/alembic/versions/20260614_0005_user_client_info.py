"""user client info

Revision ID: 20260614_0005
Revises: 20260613_0004
Create Date: 2026-06-14
"""

from alembic import op
import sqlalchemy as sa


revision = "20260614_0005"
down_revision = "20260613_0004"
branch_labels = None
depends_on = None


def table_exists(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)


def column_exists(table_name: str, column_name: str) -> bool:
    if not table_exists(table_name):
        return False
    return any(column["name"] == column_name for column in sa.inspect(op.get_bind()).get_columns(table_name))


def upgrade() -> None:
    if not column_exists("users", "last_client_app"):
        op.add_column("users", sa.Column("last_client_app", sa.String(length=80), nullable=False, server_default=""))
    if not column_exists("users", "last_client_version"):
        op.add_column("users", sa.Column("last_client_version", sa.String(length=40), nullable=False, server_default=""))
    if not column_exists("users", "last_client_version_code"):
        op.add_column("users", sa.Column("last_client_version_code", sa.Integer(), nullable=True))
    if not column_exists("users", "last_client_platform"):
        op.add_column("users", sa.Column("last_client_platform", sa.String(length=40), nullable=False, server_default=""))
    if not column_exists("users", "last_client_os_version"):
        op.add_column("users", sa.Column("last_client_os_version", sa.String(length=80), nullable=False, server_default=""))
    if not column_exists("users", "last_client_seen_at"):
        op.add_column("users", sa.Column("last_client_seen_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    for column_name in (
        "last_client_seen_at",
        "last_client_os_version",
        "last_client_platform",
        "last_client_version_code",
        "last_client_version",
        "last_client_app",
    ):
        if column_exists("users", column_name):
            op.drop_column("users", column_name)
