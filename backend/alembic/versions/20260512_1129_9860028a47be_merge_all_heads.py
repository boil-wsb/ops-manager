"""merge all heads

Revision ID: 9860028a47be
Revises: add_ops_read_to_viewer, d89ea02e6413
Create Date: 2026-05-12 11:29:28.231178

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9860028a47be'
down_revision: Union[str, None] = ('add_ops_read_to_viewer', 'd89ea02e6413')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
