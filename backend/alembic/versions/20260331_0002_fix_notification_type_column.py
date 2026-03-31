"""Fix notification_groups column name from group_type to notification_type

Revision ID: fix_notification_type_column
Revises: 20260331_0001
Create Date: 2026-03-31
"""
from alembic import op
import sqlalchemy as sa

revision = 'fix_notification_type_column'
down_revision = '20260331_0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'notification_groups',
        sa.Column('notification_type', sa.String(length=50), nullable=False, index=True, server_default='default')
    )
    op.execute("UPDATE notification_groups SET notification_type = group_type")
    op.alter_column('notification_groups', 'notification_type', server_default=None)
    op.drop_column('notification_groups', 'group_type')


def downgrade() -> None:
    op.add_column(
        'notification_groups',
        sa.Column('group_type', sa.String(length=50), nullable=False, index=True, server_default='default')
    )
    op.execute("UPDATE notification_groups SET group_type = notification_type")
    op.alter_column('notification_groups', 'group_type', server_default=None)
    op.drop_column('notification_groups', 'notification_type')