"""client operations

Revision ID: 20260613_0003
Revises: 20260611_0002
Create Date: 2026-06-13
"""

from alembic import op
import sqlalchemy as sa


revision = "20260613_0003"
down_revision = "20260611_0002"
branch_labels = None
depends_on = None


def table_exists(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)


def upgrade() -> None:
    if table_exists("client_operations"):
        return
    op.create_table(
        "client_operations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("client_operation_id", sa.String(length=64), nullable=False),
        sa.Column("operation_type", sa.String(length=80), nullable=False),
        sa.Column("temp_id", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("resource_id", sa.Integer(), nullable=True),
        sa.Column("response_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "client_operation_id", name="uq_client_operation_user_id"),
    )
    op.create_index(op.f("ix_client_operations_user_id"), "client_operations", ["user_id"], unique=False)
    op.create_index(
        op.f("ix_client_operations_client_operation_id"),
        "client_operations",
        ["client_operation_id"],
        unique=False,
    )
    op.create_index(op.f("ix_client_operations_created_at"), "client_operations", ["created_at"], unique=False)


def downgrade() -> None:
    if table_exists("client_operations"):
        op.drop_table("client_operations")
