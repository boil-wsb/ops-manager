"""merge heads

Revision ID: 46407530488f
Revises: fix_notification_type_column, 20260401_0008
Create Date: 2026-04-02 16:58:09.829668

"""
from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = '46407530488f'
down_revision: str | None = ('fix_notification_type_column', '20260401_0008')
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
