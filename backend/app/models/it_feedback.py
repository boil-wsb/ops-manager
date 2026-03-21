"""
IT Feedback model for user lag reports.
"""
import enum
from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class LagLevel(enum.StrEnum):
    """Lag severity level."""
    SLIGHT = "1"
    MODERATE = "2"
    SEVERE = "3"
    UNUSABLE = "4"


class ComputerType(enum.StrEnum):
    """Computer type."""
    DESKTOP = "desktop"
    LAPTOP = "laptop"
    WORKSTATION = "workstation"


class ITFeedback(BaseModel):
    """IT Feedback model for lag reports."""

    __tablename__ = "it_feedbacks"

    computer_type: Mapped[str] = mapped_column(String(20), nullable=False)
    usage_years: Mapped[str] = mapped_column(String(20), nullable=False)
    lag_level: Mapped[str] = mapped_column(String(1), nullable=False)
    lag_scenarios: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact: Mapped[str | None] = mapped_column(String(100), nullable=True)
    client_ip: Mapped[str | None] = mapped_column(String(45), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<ITFeedback {self.id}: {self.lag_level}>"
