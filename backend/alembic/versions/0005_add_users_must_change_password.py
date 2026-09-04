"""add users must_change_password column

为 users 表新增 must_change_password 字段（待修改初始密码标志）：
- 外部服务工号登录后若该字段为 true，签发的 token 携带 pwd_change_required 标记，
  业务接口将被全局鉴权中间件拦截（403），仅放行改密/登出/个人信息等白名单接口；
- 改密成功后置 false 并重新签发无标记 token。

存量用户默认 false（不强制），仅新同步/新建用户由代码层置 true。

Revision ID: 0005_add_users_must_change_password
Revises: 0004_add_auth_service_roles
Create Date: 2026-09-03
"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic. NOTE: version_num 列为 VARCHAR(32)，revision id 不得超过 32 字符。
revision = "0005_users_must_change_password"
down_revision = "0004_add_auth_service_roles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("users", "must_change_password")