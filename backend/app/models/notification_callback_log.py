from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.tz import now_shanghai
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
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=now_shanghai
    )
