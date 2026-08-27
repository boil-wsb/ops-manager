"""preset monitor permissions to admin/operator roles

为 admin / operator 角色预设监控配置权限（monitor:read/create/update），
供角色管理开箱即用；对已有库幂等补充分配，不覆盖角色其它已有权限。

Revision ID: 0003_preset_monitor_role_permissions
Revises: 0002_add_monitor_permissions
Create Date: 2026-08-27
"""
from sqlalchemy import text

from alembic import op

# revision identifiers, used by Alembic.
revision = "0003_preset_monitor_perm"
down_revision = "0002_add_monitor_permissions"
branch_labels = None
depends_on = None

TARGET_ROLES = ("admin", "operator")
MONITOR_CODES = ("monitor:read", "monitor:create", "monitor:update")


def upgrade() -> None:
    bind = op.get_bind()
    for role_name in TARGET_ROLES:
        role = bind.execute(
            text("SELECT id FROM roles WHERE name = :name"), {"name": role_name}
        ).first()
        if not role:
            continue
        for code in MONITOR_CODES:
            perm = bind.execute(
                text("SELECT id FROM permissions WHERE code = :code"), {"code": code}
            ).first()
            if not perm:
                continue
            exists = bind.execute(
                text(
                    "SELECT 1 FROM role_permissions WHERE role_id = :role_id AND permission_id = :perm_id"
                ),
                {"role_id": role.id, "perm_id": perm.id},
            ).first()
            if not exists:
                bind.execute(
                    text(
                        """
                        INSERT INTO role_permissions (role_id, permission_id, created_at)
                        VALUES (:role_id, :perm_id, now())
                        """
                    ),
                    {"role_id": role.id, "perm_id": perm.id},
                )


def downgrade() -> None:
    bind = op.get_bind()
    for role_name in TARGET_ROLES:
        role = bind.execute(
            text("SELECT id FROM roles WHERE name = :name"), {"name": role_name}
        ).first()
        if not role:
            continue
        for code in MONITOR_CODES:
            perm = bind.execute(
                text("SELECT id FROM permissions WHERE code = :code"), {"code": code}
            ).first()
            if not perm:
                continue
            bind.execute(
                text(
                    "DELETE FROM role_permissions WHERE role_id = :role_id AND permission_id = :perm_id"
                ),
                {"role_id": role.id, "perm_id": perm.id},
            )
