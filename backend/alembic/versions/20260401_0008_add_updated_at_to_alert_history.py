"""add updated_at to alert_history

Revision ID: 20260401_0008
Revises: 20260401_0007
Create Date: 2026-04-02

"""
from alembic import op
import sqlalchemy as sa


revision = '20260401_0008'
down_revision = '20260401_0007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'alert_history',
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    )


def downgrade() -> None:
    op.drop_column('alert_history', 'updated_at')
