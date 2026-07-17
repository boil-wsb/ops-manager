"""Change alert_history severity column from enum to varchar

Revision ID: 20260401_0007
Revises: 20260401_0006
Create Date: 2026-04-01
"""
import sqlalchemy as sa

from alembic import op

revision = "20260401_0007"
down_revision = "20260401_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        'alert_history',
        'severity',
        type_=sa.String(50),
        postgresql_using="severity::text"
    )


def downgrade() -> None:
    op.alter_column(
        'alert_history',
        'severity',
        type_=sa.Enum('info', 'warning', 'critical', name='alerthistoryseverity'),
    )
