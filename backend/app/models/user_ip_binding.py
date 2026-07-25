"""
User IP binding model for login IP restriction.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.tz import now_shanghai
from app.models.base import BaseModel


class UserIpBinding(BaseModel):
    """Bind a user to a single IP address for login restriction.

    Only applies to Feishu-synced users (whose password is their employee_no).
    Once bound, the user can only login from that IP, and that IP can only
    be used by that user.
    """

    __tablename__ = "user_ip_bindings"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )
    ip_address: Mapped[str] = mapped_column(String(45), unique=True, index=True)
    bound_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_shanghai, nullable=False
    )
