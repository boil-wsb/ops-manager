"""Add client_ip to it_feedback

Revision ID: be2745244769
Revises: 0007_add_it_feedback
Create Date: 2026-03-19 09:04:26.223551

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'be2745244769'
down_revision: str | None = '0007_add_it_feedback'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('it_feedbacks', sa.Column('client_ip', sa.String(length=45), nullable=True))
    op.create_index(op.f('ix_it_feedbacks_client_ip'), 'it_feedbacks', ['client_ip'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_it_feedbacks_client_ip'), table_name='it_feedbacks')
    op.drop_column('it_feedbacks', 'client_ip')
