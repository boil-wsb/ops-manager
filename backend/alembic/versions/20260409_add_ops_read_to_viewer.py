"""add ops:read to viewer role

Revision ID: add_ops_read_to_viewer
Revises: add_ops_permissions
Create Date: 2026-04-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'add_ops_read_to_viewer'
down_revision: Union[str, None] = 'add_ops_permissions'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r, permissions p
        WHERE r.name = 'viewer'
          AND p.code = 'ops:read'
          AND NOT EXISTS (
              SELECT 1 FROM role_permissions rp
              WHERE rp.role_id = r.id AND rp.permission_id = p.id
          )
    """)


def downgrade() -> None:
    pass
