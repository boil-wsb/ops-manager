"""Add owner_name to asset

Revision ID: 9370668b55fe
Revises: bf7b8f22ad21
Create Date: 2026-03-19 14:21:37.717780

[DEPRECATED] This migration is redundant - owner_name was already added by bf7b8f22ad21.
This file is kept for history but upgrade() does nothing.

"""
from collections.abc import Sequence

revision: str = '9370668b55fe'
down_revision: str | None = 'bf7b8f22ad21'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
