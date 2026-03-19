"""Add owner_name to asset

Revision ID: 9370668b55fe
Revises: bf7b8f22ad21
Create Date: 2026-03-19 14:21:37.717780

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '9370668b55fe'
down_revision: Union[str, None] = 'bf7b8f22ad21'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('assets', sa.Column('owner_name', sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column('assets', 'owner_name')
