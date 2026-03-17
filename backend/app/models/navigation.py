"""
Navigation link model for external quick links.
"""
from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, Boolean, Integer, Table, Column, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

navigation_link_roles = Table(
    "navigation_link_roles",
    BaseModel.metadata,
    Column("navigation_link_id", Integer, ForeignKey("navigation_links.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("created_at", DateTime(timezone=True), default=datetime.utcnow),
)


class NavigationLink(BaseModel):
    """Navigation link model for external quick links."""

    __tablename__ = "navigation_links"

    category: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    icon: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    roles: Mapped[List["Role"]] = relationship(
        "Role",
        secondary=navigation_link_roles,
        backref="navigation_links",
        lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<NavigationLink {self.category}:{self.name}>"
