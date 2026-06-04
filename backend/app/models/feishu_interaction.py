from typing import Any

from sqlalchemy import JSON, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class FeishuInteraction(BaseModel):
    __tablename__ = "feishu_interactions"

    direction: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    interaction_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    feishu_open_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    message_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    chat_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    content: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    msg_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    action_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    related_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    related_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="success")
    error: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    __table_args__ = (
        Index("idx_feishu_interactions_direction_type", "direction", "interaction_type"),
        Index("idx_feishu_interactions_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<FeishuInteraction(id={self.id}, "
            f"direction={self.direction}, "
            f"type={self.interaction_type}, "
            f"open_id={self.feishu_open_id})>"
        )
