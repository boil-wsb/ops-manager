"""Add open_message_id to it_feedbacks

Revision ID: add_open_msg_id
Revises: 20260325_0001
Create Date: 2026-03-30
"""
import sqlalchemy as sa

from alembic import op

revision = 'add_open_msg_id'
down_revision = '20260325_0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'it_feedbacks',
        sa.Column('open_message_id', sa.String(100), nullable=True, index=True)
    )


def downgrade() -> None:
    op.drop_column('it_feedbacks', 'open_message_id')
