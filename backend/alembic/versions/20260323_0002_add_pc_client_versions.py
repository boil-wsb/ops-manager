"""Add pc_client_versions table

Revision ID: 20260323_0002
Revises: 9370668b55fe
Create Date: 2026-03-23 10:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = '20260323_0002'
down_revision: str | None = '9370668b55fe'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'pc_client_versions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('version', sa.String(length=20), nullable=False),
        sa.Column('release_notes', sa.Text(), nullable=True),
        sa.Column('download_url', sa.String(length=500), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('force_update', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('min_version', sa.String(length=20), nullable=True),
        sa.Column('file_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_pc_client_versions_id'), 'pc_client_versions', ['id'], unique=False)
    op.create_index(op.f('ix_pc_client_versions_version'), 'pc_client_versions', ['version'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_pc_client_versions_version'), table_name='pc_client_versions')
    op.drop_index(op.f('ix_pc_client_versions_id'), table_name='pc_client_versions')
    op.drop_table('pc_client_versions')
