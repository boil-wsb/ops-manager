"""add unique constraint on terminal_metrics.asset_id

C-09 修复：TerminalMetric.asset_id 原本仅有 Index 无 UniqueConstraint，
并发 upsert 场景下同一 asset_id 会累积重复行，导致聚合查询把同一资产
算多遍。

修复方案：
1. 清理重复数据（保留每组 asset_id 的最大 id 行，删除其余）
2. 创建 UNIQUE 约束 uq_terminal_metric_asset_id
3. 应用层 upsert_metric / bulk_upsert_metrics 改用
   INSERT ... ON CONFLICT (asset_id) DO UPDATE（见 crud_terminal_metric.py）

Revision ID: add_terminal_metric_unique
Revises: add_history_firing_unique
Create Date: 2026-07-17 22:00:00.000000

"""
from collections.abc import Sequence

from sqlalchemy import text

from alembic import op

revision: str = "add_terminal_metric_unique"
down_revision: str | None = "add_history_firing_unique"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. 清理重复数据：保留每组 asset_id 的最大 id 行，删除其余
    op.execute(
        text(
            """
            DELETE FROM terminal_metrics
            WHERE id NOT IN (
                SELECT MAX(id) FROM terminal_metrics
                GROUP BY asset_id
            )
            """
        )
    )

    # 2. 创建 UNIQUE 约束
    op.create_unique_constraint(
        "uq_terminal_metric_asset_id",
        "terminal_metrics",
        ["asset_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_terminal_metric_asset_id", "terminal_metrics", type_="unique")
