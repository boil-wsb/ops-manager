from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class NotificationCallbackLog(BaseModel):
    __tablename__ = "notification_callback_logs"

    notification_record_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("notification_records.id"), nullable=True
    )
    callback_url: Mapped[str] = mapped_column(String(500), nullable=False)
    request_body: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    response_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # created_at 继承自 BaseModel，统一使用 DB 时钟 (server_default=func.now())
