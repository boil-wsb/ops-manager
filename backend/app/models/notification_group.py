"""
Notification group model for configurable notifications.
"""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

notification_group_members = Table(
    "notification_group_members",
    BaseModel.metadata,
    Column("notification_group_id", Integer, ForeignKey("notification_groups.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("created_at", DateTime(timezone=True), default=datetime.utcnow),
)


class NotificationGroup(BaseModel):
    """Notification group model."""

    __tablename__ = "notification_groups"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notification_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    members: Mapped[list["User"]] = relationship(
        "User",
        secondary=notification_group_members,
        backref="notification_groups",
        lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<NotificationGroup {self.name}>"