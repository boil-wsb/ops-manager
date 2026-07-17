"""add index on alert_history.starts_at

Revision ID: add_starts_at_index
Revises: add_open_msg_id_notif
Create Date: 2026-05-12 10:00:00.000000

"""
from collections.abc import Sequence

from alembic import op

revision: str = "add_starts_at_index"
down_revision: str | None = "add_open_msg_id_notif"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index("idx_alert_history_starts_at", "alert_history", ["starts_at"])


def downgrade() -> None:
    op.drop_index("idx_alert_history_starts_at", table_name="alert_history")
