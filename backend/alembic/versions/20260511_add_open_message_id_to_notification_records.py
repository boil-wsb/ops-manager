"""add open_message_id to notification_records

Revision ID: add_open_msg_id_notif
Revises: create_feishu_interactions
Create Date: 2026-05-11 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "add_open_msg_id_notif"
down_revision: Union[str, None] = "create_feishu_interactions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "notification_records",
        sa.Column("open_message_id", sa.String(length=100), nullable=True),
    )
    op.create_index(
        "ix_notification_records_open_message_id",
        "notification_records",
        ["open_message_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_notification_records_open_message_id", table_name="notification_records")
    op.drop_column("notification_records", "open_message_id")
