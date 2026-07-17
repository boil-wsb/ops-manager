"""add unique constraint on alert_card_messages (alert_history_id, recipient_open_id)

C-06 修复：防止重试/并发对同一收件人产生多条 firing 记录，导致 resolved 只能更新一条。
当前表无重复数据（2026-07-17 验证：223 条记录，0 个重复组），可直接加约束。

Revision ID: add_card_msg_unique
Revises: create_card_msg
Create Date: 2026-07-17 04:00:00.000000

"""
from collections.abc import Sequence

from alembic import op

revision: str = "add_card_msg_unique"
down_revision: str | None = "create_card_msg"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 当前表已验证无重复数据（2026-07-17），可直接加约束
    # 若未来执行此迁移时存在重复数据，需先清理：
    #   DELETE FROM alert_card_messages a USING alert_card_messages b
    #   WHERE a.id < b.id AND a.alert_history_id = b.alert_history_id
    #   AND a.recipient_open_id = b.recipient_open_id;
    op.create_unique_constraint(
        "uq_alert_card_msg_recipient",
        "alert_card_messages",
        ["alert_history_id", "recipient_open_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_alert_card_msg_recipient", "alert_card_messages", type_="unique"
    )
