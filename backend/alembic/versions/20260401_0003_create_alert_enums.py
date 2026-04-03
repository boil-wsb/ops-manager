"""Create alert_history_status and alert_history_severity enum types

Revision ID: 20260401_0003
Revises: 20260401_0002
Create Date: 2026-04-01
"""
from alembic import op
import sqlalchemy as sa

revision = "20260401_0003"
down_revision = "20260401_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if enum type exists, if not create it
    conn = op.get_bind()

    # Create status enum type
    result = conn.execute(sa.text(
        "SELECT 1 FROM pg_type WHERE typname = 'alerthistorystatus'"
    ))
    if not result.fetchone():
        conn.execute(sa.text(
            "CREATE TYPE alerthistorystatus AS ENUM ('firing', 'resolved', 'suppressed')"
        ))

    # Create severity enum type
    result = conn.execute(sa.text(
        "SELECT 1 FROM pg_type WHERE typname = 'alerthistoryseverity'"
    ))
    if not result.fetchone():
        conn.execute(sa.text(
            "CREATE TYPE alerthistoryseverity AS ENUM ('info', 'warning', 'critical')"
        ))

    # Alter columns to use enum type
    op.alter_column(
        'alert_history',
        'status',
        type_=sa.Enum('firing', 'resolved', 'suppressed', name='alerthistorystatus', create_type=False),
        postgresql_using="status::alerthistorystatus"
    )

    op.alter_column(
        'alert_history',
        'severity',
        type_=sa.Enum('info', 'warning', 'critical', name='alerthistoryseverity', create_type=False),
        postgresql_using="severity::alerthistoryseverity"
    )


def downgrade() -> None:
    op.alter_column(
        'alert_history',
        'status',
        type_=sa.String(20),
    )

    op.alter_column(
        'alert_history',
        'severity',
        type_=sa.String(20),
    )

    op.execute("DROP TYPE IF EXISTS alerthistorystatus")
    op.execute("DROP TYPE IF EXISTS alerthistoryseverity")
