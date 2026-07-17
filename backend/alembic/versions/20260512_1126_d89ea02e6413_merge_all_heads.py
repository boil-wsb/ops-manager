"""merge all heads

Revision ID: d89ea02e6413
Revises: add_chat_id_receive_type, create_feishu_interactions, add_starts_at_index
Create Date: 2026-05-12 11:26:49.457114

"""
from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = 'd89ea02e6413'
down_revision: str | None = ('add_chat_id_receive_type', 'create_feishu_interactions', 'add_starts_at_index')
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
