"""add user_ip_bindings table

IP 绑定限制：飞书同步用户（工号作为密码）首次登录时绑定 IP，
之后该用户只能从该 IP 登录，该 IP 也只能登录该用户。
防止工号公开导致的越权登录。

Revision ID: add_user_ip_bindings
Revises: add_employee_id_to_users
Create Date: 2026-07-24 12:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "add_user_ip_bindings"
down_revision: str | None = "add_employee_id_to_users"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_ip_bindings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("ip_address", sa.String(length=45), nullable=False),
        sa.Column(
            "bound_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_ip_bindings_user_id", "user_ip_bindings", ["user_id"], unique=True)
    op.create_index("ix_user_ip_bindings_ip_address", "user_ip_bindings", ["ip_address"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_user_ip_bindings_ip_address", table_name="user_ip_bindings")
    op.drop_index("ix_user_ip_bindings_user_id", table_name="user_ip_bindings")
    op.drop_table("user_ip_bindings")
