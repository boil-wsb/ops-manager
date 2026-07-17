"""
Alert management models.
"""

import enum
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class TemplateType(enum.StrEnum):
    """Alert template type enum."""

    EMAIL = "email"
    FEISHU = "feishu"


class AlertSilence(BaseModel):
    """Alert silence rule model."""

    __tablename__ = "alert_silences"

    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    # Labels to match alerts, stored as JSON
    match_labels: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    # Optional regex pattern for more complex matching
    match_pattern: Mapped[str | None] = mapped_column(Text, nullable=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<AlertSilence {self.name}>"


class AlertTemplate(BaseModel):
    """Alert notification template model."""

    __tablename__ = "alert_templates"

    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    template_type: Mapped[TemplateType] = mapped_column(
        SQLEnum(TemplateType, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    subject_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_template: Mapped[str] = mapped_column(Text, nullable=False)
    card_config: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<AlertTemplate {self.name}: {self.template_type}>"


class AlertHistoryStatus(enum.StrEnum):
    """Alert history status enum."""

    FIRING = "firing"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


class AlertHistory(BaseModel):
    """Alert history record model."""

    __tablename__ = "alert_history"
    __table_args__ = (
        # 复合表达式索引：加速 alertname + instance + starts_at 的去重查询
        # 不加 UNIQUE 约束以兼容历史数据；并发去重由 P0 预占位标记 + P1 唯一性检查保障
        Index(
            "ix_alert_history_dedup",
            "alertname",
            text("(labels ->> 'instance')"),
            "starts_at",
        ),
    )

    alertname: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    severity: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # Alert labels as JSON
    labels: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    # Alert annotations as JSON
    annotations: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_suppressed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    silence_id: Mapped[int | None] = mapped_column(
        ForeignKey("alert_silences.id", ondelete="SET NULL"), nullable=True
    )
    notification_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Deprecated: 保留以兼容历史数据查询，新代码请使用 AlertCardMessage 表
    # 根因：单值字段无法表达 1:N 关系（一个告警 → N 个收件人 → N 张卡片）
    feishu_open_message_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    def __repr__(self) -> str:
        return f"<AlertHistory {self.alertname}: {self.status}>"


class AlertCardMessage(BaseModel):
    """告警卡片消息记录：每个收件人一张飞书卡片（1:N 关联 alert_history）.

    修复根因（2026-07-17）：
    旧 feishu_open_message_id 单值字段只保存第一个收件人的 message_id，
    resolved 时只更新一张卡片，其余 N-1 张永久停留在 firing 状态。
    新表正确建模 1:N 关系，firing 批量插入，resolved 遍历更新所有卡片。
    """

    __tablename__ = "alert_card_messages"
    __table_args__ = (
        # C-06 修复: 防止重试/并发对同一收件人产生多条 firing 记录
        # 当前表无重复数据（2026-07-17 验证），可直接加约束
        UniqueConstraint(
            "alert_history_id",
            "recipient_open_id",
            name="uq_alert_card_msg_recipient",
        ),
    )

    alert_history_id: Mapped[int] = mapped_column(
        ForeignKey("alert_history.id", ondelete="CASCADE"), nullable=False, index=True
    )
    open_message_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    recipient_open_id: Mapped[str] = mapped_column(String(100), nullable=False)
    # firing / resolved
    card_status: Mapped[str] = mapped_column(String(20), default="firing", nullable=False)

    def __repr__(self) -> str:
        return f"<AlertCardMessage id={self.id} history={self.alert_history_id} status={self.card_status}>"
