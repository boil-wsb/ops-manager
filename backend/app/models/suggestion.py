"""
Suggestion model for anonymous suggestions.
"""

import enum
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class SuggestionStatus(enum.StrEnum):
    """Suggestion status lifecycle."""

    PENDING = "pending"  # 待审批（已提交，待部门负责人处理）
    APPROVED = "approved"  # 部门已审批通过（待市场部处理）
    ARCHIVED = "archived"  # 已存档（市场部已填写执行结果）
    REJECTED = "rejected"  # 已驳回


class Suggestion(BaseModel):
    """Anonymous suggestion main table."""

    __tablename__ = "suggestions"

    content: Mapped[str] = mapped_column(Text, nullable=False, comment="意见内容")
    highlights: Mapped[str | None] = mapped_column(Text, nullable=True, comment="项目服务亮点")
    innovation_ideas: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="创新/团队协助效能提高idea"
    )
    status: Mapped[str] = mapped_column(
        String(20), default=SuggestionStatus.PENDING, nullable=False, index=True, comment="状态"
    )
    query_code: Mapped[str] = mapped_column(
        String(6), unique=True, index=True, nullable=False, comment="匿名查询码"
    )
    submitter_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="提交者ID(审计用,不展示)",
    )
    client_ip: Mapped[str | None] = mapped_column(String(45), nullable=True, comment="提交IP")

    # 市场部存档字段
    market_result: Mapped[str | None] = mapped_column(Text, nullable=True, comment="市场部执行结果")
    market_reviewer_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, comment="市场部存档人"
    )
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="存档时间"
    )

    # 驳回字段
    reject_reason: Mapped[str | None] = mapped_column(Text, nullable=True, comment="驳回原因")
    rejected_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, comment="驳回人"
    )
    rejected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="驳回时间"
    )

    # 指派关系
    assignments: Mapped[list["SuggestionAssignment"]] = relationship(
        "SuggestionAssignment",
        back_populates="suggestion",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Suggestion {self.id}: {self.status}>"


class SuggestionAssignment(BaseModel):
    """Suggestion assignment to department/person for approval."""

    __tablename__ = "suggestion_assignments"

    suggestion_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("suggestions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="建议ID",
    )
    department_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
        comment="指派部门",
    )
    assignee_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, comment="指派人"
    )
    assignee_open_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="指派人飞书open_id"
    )
    open_message_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True, index=True, comment="飞书卡片消息ID"
    )
    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False, comment="pending/approved/rejected"
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="审批时间"
    )
    review_comment: Mapped[str | None] = mapped_column(Text, nullable=True, comment="审批意见")

    suggestion: Mapped["Suggestion"] = relationship("Suggestion", back_populates="assignments")
    department: Mapped["Department | None"] = relationship(
        "Department", foreign_keys=[department_id], lazy="selectin"
    )
    assignee_user: Mapped["User | None"] = relationship(
        "User", foreign_keys=[assignee_user_id], lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<SuggestionAssignment {self.id}: suggestion={self.suggestion_id} status={self.status}>"
