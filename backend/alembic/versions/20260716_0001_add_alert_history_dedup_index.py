"""add composite expression index on alert_history for dedup

加速 alertname + instance + starts_at 的去重查询。
不加 UNIQUE 约束以兼容历史数据；并发去重由 P0 预占位标记保障。

Revision ID: add_dedup_index
Revises: d2b3c4d5e6f7
Create Date: 2026-07-16 10:30:00.000000

"""
from collections.abc import Sequence

from sqlalchemy import text

from alembic import op

revision: str = "add_dedup_index"
down_revision: str | None = "d2b3c4d5e6f7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 用 text() + get_bind().execute() 绕过 asyncpg 对 ->> 操作符的 prepare 解析问题
    bind = op.get_bind()
    bind.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_alert_history_dedup "
            "ON alert_history (alertname, (labels ->> 'instance'), starts_at)"
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(text("DROP INDEX IF EXISTS ix_alert_history_dedup"))
