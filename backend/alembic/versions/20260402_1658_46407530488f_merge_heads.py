"""merge heads

Revision ID: 46407530488f
Revises: fix_notification_type_column, 20260401_0008
Create Date: 2026-04-02 16:58:09.829668

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '46407530488f'
down_revision: Union[str, None] = ('fix_notification_type_column', '20260401_0008')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
