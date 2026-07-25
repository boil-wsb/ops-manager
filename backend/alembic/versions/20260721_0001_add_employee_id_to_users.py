"""add employee_id column to users table

新增 users.employee_id 字段，用于存储从飞书通讯录同步的工号。
飞书 GetUser API 返回的 employee_no 字段会写入此列。

Revision ID: add_employee_id_to_users
Revises: add_terminal_metric_unique
Create Date: 2026-07-21 11:30:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "add_employee_id_to_users"
down_revision: str | None = "add_terminal_metric_unique"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("employee_id", sa.String(length=64), nullable=True, comment="工号"),
    )
    op.create_index("ix_users_employee_id", "users", ["employee_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_employee_id", table_name="users")
    op.drop_column("users", "employee_id")
