"""
Notification Record model for tracking Feishu notification history.
"""
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class NotificationRecord(BaseModel):
    """Notification Record model for tracking Feishu notification history."""

    __tablename__ = "notification_records"

    user: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    matched_user: Mapped[str | None] = mapped_column(String(100), nullable=True)
    feishu_open_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    card_content: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    message_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    error: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<NotificationRecord {self.id}: user={self.user}, success={self.success}>"
