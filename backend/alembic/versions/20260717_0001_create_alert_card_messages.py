"""create alert_card_messages table for multi-recipient card tracking

新建 alert_card_messages 关联表，正确建模 alert_history(1) ↔ feishu_card(N) 的 1:N 关系。
修复根因：旧 feishu_open_message_id 单值字段只保存第一个收件人的 message_id，
resolved 时只更新一张卡片，其余 N-1 张永久停留在 firing 状态。

Revision ID: create_card_msg
Revises: add_dedup_index
Create Date: 2026-07-17 02:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "create_card_msg"
down_revision: str | None = "add_dedup_index"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. 创建 alert_card_messages 表
    op.create_table(
        "alert_card_messages",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "alert_history_id",
            sa.Integer(),
            sa.ForeignKey("alert_history.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("open_message_id", sa.String(length=100), nullable=False),
        sa.Column("recipient_open_id", sa.String(length=100), nullable=False),
        sa.Column(
            "card_status", sa.String(length=20), nullable=False, server_default="firing"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # 2. 创建索引
    # 反查索引：callback_handler 通过 open_message_id 反查 alert_history
    op.create_index(
        "ix_alert_card_messages_open_message_id",
        "alert_card_messages",
        ["open_message_id"],
    )
    # 正查索引：resolved 时通过 alert_history_id 查所有卡片
    op.create_index(
        "ix_alert_card_messages_history_id",
        "alert_card_messages",
        ["alert_history_id"],
    )
    # card_status 索引：按状态过滤
    op.create_index(
        "ix_alert_card_messages_card_status",
        "alert_card_messages",
        ["card_status"],
    )

    # 3. 数据迁移：将历史 feishu_open_message_id 单值字段导入新表
    # recipient_open_id 填 'migrated'（无法反查历史收件人）
    # 过滤空字符串避免脏数据（I-20 修复）
    op.execute(
        "INSERT INTO alert_card_messages (alert_history_id, open_message_id, recipient_open_id, card_status) "
        "SELECT id, feishu_open_message_id, 'migrated', 'firing' "
        "FROM alert_history WHERE feishu_open_message_id IS NOT NULL AND feishu_open_message_id != ''"
    )


def downgrade() -> None:
    op.drop_index("ix_alert_card_messages_card_status", table_name="alert_card_messages")
    op.drop_index("ix_alert_card_messages_history_id", table_name="alert_card_messages")
    op.drop_index("ix_alert_card_messages_open_message_id", table_name="alert_card_messages")
    op.drop_table("alert_card_messages")
