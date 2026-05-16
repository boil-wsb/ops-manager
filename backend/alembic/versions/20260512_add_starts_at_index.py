"""add index on alert_history.starts_at

Revision ID: add_starts_at_index
Revises: add_open_msg_id_notif
Create Date: 2026-05-12 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "add_starts_at_index"
down_revision: Union[str, None] = "add_open_msg_id_notif"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("idx_alert_history_starts_at", "alert_history", ["starts_at"])


def downgrade() -> None:
    op.drop_index("idx_alert_history_starts_at", table_name="alert_history")
