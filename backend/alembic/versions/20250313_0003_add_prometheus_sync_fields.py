"""
Add Prometheus sync fields to assets table

Revision ID: 20250313_0003
Revises: 20250313_0002
Create Date: 2026-03-13
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0003_add_prometheus_sync_fields'
down_revision: str | None = '0002_add_audit_logs'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add Prometheus sync fields to assets table."""
    # Create enum types
    asset_source_enum = postgresql.ENUM('manual', 'prometheus', 'imported', name='assetsource')
    asset_source_enum.create(op.get_bind())

    sync_status_enum = postgresql.ENUM('pending', 'synced', 'error', name='syncstatus')
    sync_status_enum.create(op.get_bind())

    # Add new columns to assets table
    op.add_column('assets', sa.Column('arch', sa.String(50), nullable=True))
    op.add_column('assets', sa.Column('source', sa.Enum('manual', 'prometheus', 'imported', name='assetsource'),
                                      nullable=False, server_default='manual'))
    op.add_column('assets', sa.Column('prometheus_instance', sa.String(255), nullable=True))
    op.add_column('assets', sa.Column('last_sync_time', sa.DateTime(timezone=True), nullable=True))
    op.add_column('assets', sa.Column('sync_status', sa.Enum('pending', 'synced', 'error', name='syncstatus'),
                                      nullable=False, server_default='pending'))

    # Create index on source column for faster filtering
    op.create_index('ix_assets_source', 'assets', ['source'])
    op.create_index('ix_assets_sync_status', 'assets', ['sync_status'])


def downgrade() -> None:
    """Remove Prometheus sync fields from assets table."""
    # Drop indexes
    op.drop_index('ix_assets_sync_status', table_name='assets')
    op.drop_index('ix_assets_source', table_name='assets')

    # Drop columns
    op.drop_column('assets', 'sync_status')
    op.drop_column('assets', 'last_sync_time')
    op.drop_column('assets', 'prometheus_instance')
    op.drop_column('assets', 'source')
    op.drop_column('assets', 'arch')

    # Drop enum types
    sync_status_enum = postgresql.ENUM('pending', 'synced', 'error', name='syncstatus')
    sync_status_enum.drop(op.get_bind())

    asset_source_enum = postgresql.ENUM('manual', 'prometheus', 'imported', name='assetsource')
    asset_source_enum.drop(op.get_bind())
