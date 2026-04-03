"""
Alert management models.
"""
import enum
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
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
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
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
        nullable=False
    )
    subject_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_template: Mapped[str] = mapped_column(Text, nullable=False)
    card_config: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True
    )
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
        ForeignKey("alert_silences.id", ondelete="SET NULL"),
        nullable=True
    )
    notification_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    feishu_open_message_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    def __repr__(self) -> str:
        return f"<AlertHistory {self.alertname}: {self.status}>"
