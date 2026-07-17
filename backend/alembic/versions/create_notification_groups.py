"""Create notification_groups and notification_group_members tables

Revision ID: 20260331_0001
Revises: add_open_msg_id
Create Date: 2026-03-31
"""
import sqlalchemy as sa

from alembic import op

revision = '20260331_0001'
down_revision = 'add_open_msg_id'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'notification_groups',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('notification_type', sa.String(length=50), nullable=False, index=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'notification_group_members',
        sa.Column('notification_group_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['notification_group_id'], ['notification_groups.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('notification_group_id', 'user_id')
    )


def downgrade() -> None:
    op.drop_table('notification_group_members')
    op.drop_table('notification_groups')
