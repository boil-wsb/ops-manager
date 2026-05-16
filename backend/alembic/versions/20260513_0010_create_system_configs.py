"""create system_configs table

Revision ID: 20260513_0010
Revises: 20260512_0010
Create Date: 2026-05-13 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260513_0010"
down_revision: Union[str, None] = "20260512_0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "system_configs",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("key", sa.String(200), unique=True, nullable=False, index=True),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("group", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_secret", sa.Boolean(), default=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_system_configs_group", "system_configs", ["group"])


def downgrade() -> None:
    op.drop_index("ix_system_configs_group", table_name="system_configs")
    op.drop_table("system_configs")
