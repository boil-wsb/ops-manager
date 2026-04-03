"""Change alert_history status column from enum to varchar

Revision ID: 20260401_0004
Revises: 20260401_0003
Create Date: 2026-04-01
"""
from alembic import op
import sqlalchemy as sa

revision = "20260401_0004"
down_revision = "20260401_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        'alert_history',
        'status',
        type_=sa.String(20),
        postgresql_using="status::text"
    )


def downgrade() -> None:
    op.alter_column(
        'alert_history',
        'status',
        type_=sa.Enum('firing', 'resolved', 'suppressed', name='alerthistorystatus'),
    )
