"""add matched_user and success columns to notification_records

Revision ID: add_matched_user
Revises: c224b325618a
Create Date: 2026-04-08 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'add_matched_user'
down_revision: Union[str, None] = 'c224b325618a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('notification_records', sa.Column('matched_user', sa.String(length=100), nullable=True))
    op.add_column('notification_records', sa.Column('success', sa.Boolean(), nullable=True, default=False))
    op.drop_column('notification_records', 'status')
    op.drop_column('notification_records', 'error_message')
    op.drop_column('notification_records', 'template_id')
    op.drop_column('notification_records', 'template_name')
    op.drop_column('notification_records', 'notification_type')
    op.alter_column('notification_records', 'card_content', type_=sa.JSON(), nullable=True)


def downgrade() -> None:
    pass