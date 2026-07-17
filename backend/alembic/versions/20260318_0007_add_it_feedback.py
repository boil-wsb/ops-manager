"""add it_feedback table

Revision ID: 0007_add_it_feedback
Revises: 0006_add_terminal_enum
Create Date: 2026-03-18

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = '0007_add_it_feedback'
down_revision: str | None = '0006_add_terminal_enum'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'it_feedbacks',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('computer_type', sa.String(length=20), nullable=False),
        sa.Column('usage_years', sa.String(length=20), nullable=False),
        sa.Column('lag_level', sa.String(length=1), nullable=False),
        sa.Column('lag_scenarios', sa.Text(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('contact', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=20), server_default='pending', nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_by', sa.String(length=100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_it_feedbacks_id', 'it_feedbacks', ['id'], unique=False)
    op.create_index('ix_it_feedbacks_status', 'it_feedbacks', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_it_feedbacks_status', table_name='it_feedbacks')
    op.drop_index('ix_it_feedbacks_id', table_name='it_feedbacks')
    op.drop_table('it_feedbacks')
