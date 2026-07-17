"""Add feishu user sync fields

Revision ID: 20260325_0001
Revises: 20260323_0002
Create Date: 2026-03-25 10:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = '20260325_0001'
down_revision: str | None = '20260323_0002'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('users', sa.Column('feishu_open_id', sa.String(length=64), nullable=True))
    op.add_column('users', sa.Column('feishu_union_id', sa.String(length=64), nullable=True))
    op.add_column('users', sa.Column('feishu_sync_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('is_feishu_user', sa.Boolean(), nullable=False, server_default=sa.text('false')))

    op.create_index(op.f('ix_users_feishu_open_id'), 'users', ['feishu_open_id'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_users_feishu_open_id'), table_name='users')
    op.drop_column('users', 'is_feishu_user')
    op.drop_column('users', 'feishu_sync_at')
    op.drop_column('users', 'feishu_union_id')
    op.drop_column('users', 'feishu_open_id')
