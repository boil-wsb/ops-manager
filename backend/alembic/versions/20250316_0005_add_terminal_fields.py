"""
Add terminal asset fields and type

Revision ID: 20250316_0005
Revises: 0004_create_navigation_links
Create Date: 2026-03-16
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = '0005_add_terminal_fields'
down_revision: str | None = '0004_create_navigation_links'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add terminal asset fields."""
    op.add_column('assets', sa.Column('hostname', sa.String(100), nullable=True))
    op.add_column('assets', sa.Column('serial_number', sa.String(100), nullable=True))
    op.add_column('assets', sa.Column('uuid', sa.String(100), nullable=True))
    op.add_column('assets', sa.Column('customer', sa.String(100), nullable=True))

    op.create_index('ix_assets_hostname', 'assets', ['hostname'])


def downgrade() -> None:
    """Remove terminal asset fields."""
    op.drop_index('ix_assets_hostname', table_name='assets')
    op.drop_column('assets', 'customer')
    op.drop_column('assets', 'uuid')
    op.drop_column('assets', 'serial_number')
    op.drop_column('assets', 'hostname')
