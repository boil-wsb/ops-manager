"""add_suggestion_permissions

Revision ID: d2b3c4d5e6f7
Revises: c1a2b3c4d5e6
Create Date: 2026-07-14 00:02:00.000000

"""
from collections.abc import Sequence

from alembic import op

revision: str = 'd2b3c4d5e6f7'
down_revision: str | None = 'c1a2b3c4d5e6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. 插入三个权限码
    op.execute("""
        INSERT INTO permissions (code, name, module, action, description, is_active, created_at, updated_at)
        VALUES
            ('suggestion:submit', '提交匿名建议', 'suggestion', 'submit', '提交匿名建议', true, NOW(), NOW()),
            ('suggestion:read', '查看建议列表', 'suggestion', 'read', '查看匿名建议列表与详情', true, NOW(), NOW()),
            ('suggestion:archive', '市场部存档建议', 'suggestion', 'archive', '市场部填写执行结果并存档', true, NOW(), NOW())
        ON CONFLICT (code) DO NOTHING
    """)

    # 2. 将 suggestion:submit 赋予所有现有角色
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id, created_at)
        SELECT r.id, p.id, NOW()
        FROM roles r
        CROSS JOIN permissions p
        WHERE p.code = 'suggestion:submit'
          AND r.is_active = true
          AND NOT EXISTS (
              SELECT 1 FROM role_permissions rp
              WHERE rp.role_id = r.id AND rp.permission_id = p.id
          )
    """)

    # 3. 将 suggestion:read 赋予管理员角色（name 包含 admin 或 is_system）
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id, created_at)
        SELECT r.id, p.id, NOW()
        FROM roles r
        CROSS JOIN permissions p
        WHERE p.code = 'suggestion:read'
          AND r.is_active = true
          AND (r.is_system = true OR LOWER(r.name) LIKE '%admin%' OR LOWER(r.name) LIKE '%管理%')
          AND NOT EXISTS (
              SELECT 1 FROM role_permissions rp
              WHERE rp.role_id = r.id AND rp.permission_id = p.id
          )
    """)

    # 4. 将 suggestion:archive 赋予管理员角色
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id, created_at)
        SELECT r.id, p.id, NOW()
        FROM roles r
        CROSS JOIN permissions p
        WHERE p.code = 'suggestion:archive'
          AND r.is_active = true
          AND (r.is_system = true OR LOWER(r.name) LIKE '%admin%' OR LOWER(r.name) LIKE '%管理%')
          AND NOT EXISTS (
              SELECT 1 FROM role_permissions rp
              WHERE rp.role_id = r.id AND rp.permission_id = p.id
          )
    """)

    # 5. 初始化市场部负责人通知组（空成员，管理员后续在界面配置）
    # I-08 修复：notification_groups 表无 UNIQUE 约束，ON CONFLICT DO NOTHING
    # 无目标约束时不会触发去重，迁移回滚重跑会产生重复行。改用 WHERE NOT EXISTS
    # 子查询按 notification_type 显式查重。
    op.execute("""
        INSERT INTO notification_groups (name, description, notification_type, is_active, created_at, updated_at)
        SELECT
            '市场部建议审批通知组',
            '匿名建议审批通过后转市场部负责人，成员将收到待执行卡片',
            'suggestion_market_review',
            true,
            NOW(),
            NOW()
        WHERE NOT EXISTS (
            SELECT 1 FROM notification_groups WHERE notification_type = 'suggestion_market_review'
        )
    """)


def downgrade() -> None:
    op.execute("DELETE FROM role_permissions WHERE permission_id IN (SELECT id FROM permissions WHERE code LIKE 'suggestion:%')")
    op.execute("DELETE FROM permissions WHERE code LIKE 'suggestion:%'")
    op.execute("DELETE FROM notification_groups WHERE notification_type = 'suggestion_market_review'")
