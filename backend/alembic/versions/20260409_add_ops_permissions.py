"""add ops permissions

Revision ID: add_ops_permissions
Revises: add_memory_disk_total_gb
Create Date: 2026-04-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'add_ops_permissions'
down_revision: Union[str, None] = 'add_memory_disk_total_gb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        INSERT INTO permissions (code, name, module, action, description, is_active, created_at, updated_at)
        VALUES
            ('ops:read', '查看运维', 'ops', 'read', '查看运维管理', true, NOW(), NOW()),
            ('ops:write', '编辑运维', 'ops', 'write', '编辑运维管理', true, NOW(), NOW()),
            ('ops:delete', '删除运维', 'ops', 'delete', '删除运维管理', true, NOW(), NOW())
        ON CONFLICT (code) DO NOTHING
    """)


def downgrade() -> None:
    pass
