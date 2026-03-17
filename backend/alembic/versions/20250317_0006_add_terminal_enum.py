"""
Add TERMINAL to assettype enum

Revision ID: 20250317_0006
Revises: 0005_add_terminal_fields
Create Date: 2026-03-17
"""
from typing import Sequence, Union

from alembic import op

revision: str = '0006_add_terminal_enum'
down_revision: Union[str, None] = '0005_add_terminal_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE assettype ADD VALUE IF NOT EXISTS 'TERMINAL'")


def downgrade() -> None:
    pass
