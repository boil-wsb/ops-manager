"""
Notification Record model for tracking Feishu notification history.
"""

from sqlalchemy import JSON, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class NotificationRecord(BaseModel):
    """Notification Record model for tracking Feishu notification history."""

    __tablename__ = "notification_records"

    user: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    matched_user: Mapped[str | None] = mapped_column(String(100), nullable=True)
    feishu_open_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    chat_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    receive_type: Mapped[str] = mapped_column(String(20), nullable=False, default="open_id")
    callback_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    open_message_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    callback_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    card_content: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    message_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    error: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    # created_at 和 updated_at 均继承自 BaseModel，统一使用 DB 时钟 (server_default=func.now())
    # 历史 bug: created_at 用 Python now_shanghai()，updated_at 用 DB func.now()，
    # 两个时钟源导致 updated_at < created_at 的不可能时序。

    def __repr__(self) -> str:
        return f"<NotificationRecord {self.id}: user={self.user}, success={self.success}>"
