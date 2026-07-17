"""add chat_id and receive_type to notification_records

Revision ID: add_chat_id_receive_type
Revises: add_callback_id
Create Date: 2026-05-11 10:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "add_chat_id_receive_type"
down_revision: str | None = "add_callback_id"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "notification_records",
        sa.Column("chat_id", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "notification_records",
        sa.Column("receive_type", sa.String(length=20), nullable=False, server_default="open_id"),
    )
    op.create_index(
        "ix_notification_records_chat_id",
        "notification_records",
        ["chat_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_notification_records_chat_id", table_name="notification_records")
    op.drop_column("notification_records", "receive_type")
    op.drop_column("notification_records", "chat_id")
