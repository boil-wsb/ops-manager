"""add partial unique index on alert_history for firing dedup

C-04 终极方案：在 alert_history 上创建部分唯一索引，仅对 status='firing' 的记录
强制 (alertname, instance, starts_at) 唯一。配合应用层 IntegrityError 捕获重试，
彻底解决 TOCTOU 竞态：并发 webhook 同时 SELECT 返回 None 时，第二个 INSERT 会被
部分唯一索引拒绝。

设计要点：
- WHERE status='firing' 不影响历史 resolved 数据（兼容项目约束「不加 UNIQUE 约束」）
- 合法 flap 场景（firing→resolved→firing）不冲突：第一条已 resolved，不在索引范围
- 表达式索引 (labels->>'instance') 与已有 ix_alert_history_dedup 一致，asyncpg 已验证可行
- 用 text() + get_bind().execute() 绕过 asyncpg 对 ->> 操作符的 prepare 解析问题（I-11）

Revision ID: add_history_firing_unique
Revises: add_card_msg_unique
Create Date: 2026-07-17 05:00:00.000000

"""
from collections.abc import Sequence

from sqlalchemy import text

from alembic import op

revision: str = "add_history_firing_unique"
down_revision: str | None = "add_card_msg_unique"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 先清理 firing 状态的重复数据（保留 id 最大的一条）
    # 注意：仅在 status='firing' 范围内清理，不影响 resolved/suppressed 记录
    bind = op.get_bind()
    bind.execute(
        text(
            "DELETE FROM alert_history a USING alert_history b "
            "WHERE a.id < b.id AND a.status = 'firing' AND b.status = 'firing' "
            "AND a.alertname = b.alertname "
            "AND a.labels->>'instance' = b.labels->>'instance' "
            "AND a.starts_at = b.starts_at"
        )
    )

    # 创建部分唯一索引（仅对 firing 状态唯一）
    # 用 text() + get_bind().execute() 绕过 asyncpg 的 ->> prepare 解析问题
    bind.execute(
        text(
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_alert_history_firing_unique "
            "ON alert_history (alertname, (labels ->> 'instance'), starts_at) "
            "WHERE status = 'firing'"
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(text("DROP INDEX IF EXISTS ix_alert_history_firing_unique"))
