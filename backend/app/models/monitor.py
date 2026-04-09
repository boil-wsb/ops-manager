"""
Monitoring and alerting models.
"""

import enum
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class MonitorType(enum.StrEnum):
    """Monitor type enum."""

    PING = "ping"
    HTTP = "http"
    TCP = "tcp"
    UDP = "udp"


class MonitorStatus(enum.StrEnum):
    """Monitor status enum."""

    UP = "up"
    DOWN = "down"
    UNKNOWN = "unknown"
    PAUSED = "paused"


class Monitor(BaseModel):
    """Monitor configuration model."""

    __tablename__ = "monitors"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    monitor_type: Mapped[MonitorType] = mapped_column(SQLEnum(MonitorType), nullable=False)
    target: Mapped[str] = mapped_column(String(500), nullable=False)  # IP, URL, etc.

    # Check configuration
    interval_seconds: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=3, nullable=False)

    # HTTP specific
    http_method: Mapped[str | None] = mapped_column(String(10), nullable=True)  # GET, POST, etc.
    http_headers: Mapped[dict[str, str] | None] = mapped_column(JSON, nullable=True)
    http_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    expected_response_content: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Alert thresholds
    threshold_warning: Mapped[float | None] = mapped_column(Float, nullable=True)
    threshold_critical: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Status
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    current_status: Mapped[MonitorStatus] = mapped_column(
        SQLEnum(MonitorStatus), default=MonitorStatus.UNKNOWN, nullable=False
    )
    last_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_check_result: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_check_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Associated asset
    asset_id: Mapped[int | None] = mapped_column(
        ForeignKey("assets.id", ondelete="SET NULL"), nullable=True
    )
    asset: Mapped[Optional["Asset"]] = relationship("Asset", back_populates="monitors")

    # Relationships
    alerts: Mapped[list["Alert"]] = relationship("Alert", back_populates="monitor", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Monitor {self.name}: {self.target}>"


class AlertSeverity(enum.StrEnum):
    """Alert severity enum."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertStatus(enum.StrEnum):
    """Alert status enum."""

    FIRING = "firing"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


class Alert(BaseModel):
    """Alert event model."""

    __tablename__ = "alerts"

    monitor_id: Mapped[int] = mapped_column(
        ForeignKey("monitors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    monitor: Mapped["Monitor"] = relationship("Monitor", back_populates="alerts")

    alert_rule_id: Mapped[int | None] = mapped_column(
        ForeignKey("alert_rules.id", ondelete="SET NULL"), nullable=True
    )

    severity: Mapped[AlertSeverity] = mapped_column(
        SQLEnum(AlertSeverity), default=AlertSeverity.WARNING, nullable=False
    )
    status: Mapped[AlertStatus] = mapped_column(
        SQLEnum(AlertStatus), default=AlertStatus.FIRING, nullable=False
    )

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Metric data
    metric_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    metric_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    threshold_value: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Timeline
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Notification
    notification_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notification_channels: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)

    def __repr__(self) -> str:
        return f"<Alert {self.title}: {self.status}>"


class AlertRule(BaseModel):
    """Alert rule configuration model."""

    __tablename__ = "alert_rules"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Condition
    condition_expression: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # e.g., "response_time > 1000"
    duration_seconds: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )  # 0 = immediate
    severity: Mapped[AlertSeverity] = mapped_column(
        SQLEnum(AlertSeverity), default=AlertSeverity.WARNING, nullable=False
    )

    # Notification
    notification_channels: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    notification_template: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Suppression
    suppress_interval_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<AlertRule {self.name}>"


class NotificationChannelType(enum.StrEnum):
    """Notification channel type enum."""

    EMAIL = "email"
    WEBHOOK = "webhook"
    SMS = "sms"


class NotificationChannel(BaseModel):
    """Notification channel configuration model."""

    __tablename__ = "notification_channels"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    channel_type: Mapped[NotificationChannelType] = mapped_column(
        SQLEnum(NotificationChannelType), nullable=False
    )

    # Configuration (encrypted in production)
    config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    # e.g., for email: {"smtp_host": "...", "to_addresses": [...]}
    # e.g., for webhook: {"url": "...", "method": "POST", "headers": {...}}

    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Test status
    last_test_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_test_status: Mapped[str | None] = mapped_column(String(20), nullable=True)

    def __repr__(self) -> str:
        return f"<NotificationChannel {self.name}: {self.channel_type}>"
