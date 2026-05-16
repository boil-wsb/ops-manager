"""add callback_id column to notification_records

Revision ID: add_callback_id
Revises: add_matched_user
Create Date: 2026-04-10 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "add_callback_id"
down_revision: Union[str, None] = "add_matched_user"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "notification_records",
        sa.Column("callback_id", sa.String(length=100), nullable=True),
    )
    op.create_index(
        "ix_notification_records_callback_id",
        "notification_records",
        ["callback_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_notification_records_callback_id", table_name="notification_records")
    op.drop_column("notification_records", "callback_id")
