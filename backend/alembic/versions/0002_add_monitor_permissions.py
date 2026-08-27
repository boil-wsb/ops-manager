"""add monitor permissions

注册监控主机配置权限（monitor:read/create/update），使角色管理界面可分配给非 admin 角色。
对已有库幂等：权限已存在则跳过，不重置任何角色已有权限分配。

Revision ID: 0002_add_monitor_permissions
Revises: 0001_baseline_full_schema
Create Date: 2026-08-27
"""
from sqlalchemy import text

from alembic import op

# revision identifiers, used by Alembic.
revision = "0002_add_monitor_permissions"
down_revision = "0001_baseline_full_schema"
branch_labels = None
depends_on = None

MONITOR_PERMISSIONS = [
    {
        "code": "monitor:read",
        "name": "查看监控配置",
        "module": "monitor",
        "action": "read",
        "description": "查看监控主机配置",
    },
    {
        "code": "monitor:create",
        "name": "新增监控主机",
        "module": "monitor",
        "action": "create",
        "description": "新增监控主机配置",
    },
    {
        "code": "monitor:update",
        "name": "编辑监控配置",
        "module": "monitor",
        "action": "update",
        "description": "编辑与提交监控主机配置",
    },
]


def upgrade() -> None:
    bind = op.get_bind()
    for perm in MONITOR_PERMISSIONS:
        exists = bind.execute(
            text("SELECT 1 FROM permissions WHERE code = :code"), {"code": perm["code"]}
        ).first()
        if not exists:
            bind.execute(
                text(
                    """
                    INSERT INTO permissions (code, name, module, action, description, is_active)
                    VALUES (:code, :name, :module, :action, :description, true)
                    """
                ),
                perm,
            )


def downgrade() -> None:
    bind = op.get_bind()
    for perm in MONITOR_PERMISSIONS:
        bind.execute(text("DELETE FROM permissions WHERE code = :code"), {"code": perm["code"]})
