"""baseline full schema (squashed)

由历史 53 个迁移脚本归并生成的单一初始迁移。
应用启动依赖 app/db/init_db.py 的 Base.metadata.create_all 建表，
此迁移作为 alembic 版本基线：新库 upgrade 一键建全库，已有库仅作为版本标记。

Revision ID: 0001_baseline_full_schema
Revises:
Create Date: 2026-08-26
"""
from alembic import op

from app.models.base import BaseModel

# revision identifiers, used by Alembic.
revision = "0001_baseline_full_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """创建应用模型的完整表结构（对已存在表幂等）。"""
    bind = op.get_bind()
    BaseModel.metadata.create_all(bind=bind)


def downgrade() -> None:
    """删除全部应用模型的表。"""
    bind = op.get_bind()
    BaseModel.metadata.drop_all(bind=bind)