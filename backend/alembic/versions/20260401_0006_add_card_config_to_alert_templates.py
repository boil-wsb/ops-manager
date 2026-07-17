"""Add card_config to alert_templates

Revision ID: 20260401_0006
Revises: 20260401_0005
Create Date: 2026-04-01
"""
import sqlalchemy as sa

from alembic import op

revision = "20260401_0006"
down_revision = "20260401_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'alert_templates',
        sa.Column('card_config', sa.JSON(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('alert_templates', 'card_config')
