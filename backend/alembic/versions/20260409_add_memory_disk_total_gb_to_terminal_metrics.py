"""add memory_total_gb and disk_total_gb to terminal_metrics

Revision ID: add_memory_disk_total_gb
Revises: add_matched_user
Create Date: 2026-04-09 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'add_memory_disk_total_gb'
down_revision: str | None = 'add_matched_user'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('terminal_metrics', sa.Column('memory_total_gb', sa.Float(), nullable=True))
    op.add_column('terminal_metrics', sa.Column('disk_total_gb', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('terminal_metrics', 'memory_total_gb')
    op.drop_column('terminal_metrics', 'disk_total_gb')
