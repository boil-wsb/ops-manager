"""
Department model for Feishu organizational structure.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Department(BaseModel):
    """Department model synced from Feishu."""

    __tablename__ = "departments"

    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="部门名称")
    feishu_department_id: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False, comment="飞书部门ID"
    )
    parent_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, comment="父部门ID"
    )
    feishu_parent_department_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="飞书父部门ID"
    )
    is_root: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="是否根部门"
    )
    member_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, comment="部门成员数"
    )
    sync_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="最后同步时间"
    )
    leader_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, comment="部门负责人"
    )

    # Relationships
    children: Mapped[list["Department"]] = relationship(
        "Department",
        backref="parent_dept",
        remote_side="Department.id",
        foreign_keys="Department.parent_id",
        lazy="selectin",
    )
    users: Mapped[list["User"]] = relationship(
        "User",
        back_populates="department",
        foreign_keys="User.department_id",
        lazy="selectin",
    )
    leader: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[leader_id],
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Department {self.name}>"
