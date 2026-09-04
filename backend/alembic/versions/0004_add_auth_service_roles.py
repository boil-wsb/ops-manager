"""add auth service roles and role code column

1. 为 roles 表新增 code 列（稳定 ASCII 标识，供外部鉴权服务匹配）；
2. 幂等回填现有内置角色 code（superadmin/admin/operator/viewer）；
3. 幂等预置三个业务角色：行政(admin_dept)、采购(procurement)、营销(marketing)，
   供「工号角色校验」外部鉴权接口使用（is_system=false，可在角色管理中正常增删改）。

Revision ID: 0004_add_auth_service_roles
Revises: 0003_preset_monitor_perm
Create Date: 2026-09-03
"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0004_add_auth_service_roles"
down_revision = "0003_preset_monitor_perm"
branch_labels = None
depends_on = None

# 现有内置角色 code 回填
EXISTING_ROLE_CODES = {
    "superadmin": "superadmin",
    "admin": "admin",
    "operator": "operator",
    "viewer": "viewer",
}

# 预置业务角色（外部鉴权服务三角色）
BUSINESS_ROLES = [
    {
        "name": "行政",
        "code": "admin_dept",
        "description": "行政事务角色",
    },
    {
        "name": "采购",
        "code": "procurement",
        "description": "采购业务角色",
    },
    {
        "name": "营销",
        "code": "marketing",
        "description": "营销业务角色",
    },
]


def upgrade() -> None:
    op.add_column("roles", sa.Column("code", sa.String(50), unique=True, nullable=True))

    bind = op.get_bind()

    # 回填现有内置角色 code（仅对 code 为空的记录）
    for name, code in EXISTING_ROLE_CODES.items():
        bind.execute(
            sa.text("UPDATE roles SET code = :code WHERE name = :name AND code IS NULL"),
            {"name": name, "code": code},
        )

    # 幂等插入业务三角色
    for role in BUSINESS_ROLES:
        exists = bind.execute(
            sa.text("SELECT 1 FROM roles WHERE code = :code"), {"code": role["code"]}
        ).first()
        if not exists:
            bind.execute(
                sa.text(
                    """
                    INSERT INTO roles (name, code, description, is_system, is_active, created_at, updated_at)
                    VALUES (:name, :code, :description, false, true, now(), now())
                    """
                ),
                role,
            )


def downgrade() -> None:
    bind = op.get_bind()
    for role in BUSINESS_ROLES:
        bind.execute(
            sa.text("DELETE FROM roles WHERE code = :code"), {"code": role["code"]}
        )
    op.drop_column("roles", "code")