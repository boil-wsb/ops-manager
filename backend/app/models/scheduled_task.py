from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class ScheduledTask(BaseModel):
    __tablename__ = "scheduled_tasks"

    task_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    task_function: Mapped[str] = mapped_column(String(200), nullable=False)
    trigger_type: Mapped[str] = mapped_column(String(20), nullable=False)
    trigger_config: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_run_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    last_run_duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    next_run_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    execution_logs: Mapped[list["TaskExecutionLog"]] = relationship(
        "TaskExecutionLog", back_populates="task", lazy="selectin"
    )

    __table_args__ = (
        Index("ix_scheduled_tasks_category", "category"),
        Index("ix_scheduled_tasks_is_enabled", "is_enabled"),
    )

    def __repr__(self) -> str:
        return f"<ScheduledTask {self.task_id}: {self.name}>"


class TaskExecutionLog(BaseModel):
    __tablename__ = "task_execution_logs"

    task_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("scheduled_tasks.task_id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    trigger_type: Mapped[str] = mapped_column(String(20), nullable=False)
    triggered_by: Mapped[str | None] = mapped_column(String(100), nullable=True)

    task: Mapped["ScheduledTask"] = relationship("ScheduledTask", back_populates="execution_logs")

    __table_args__ = (
        Index("ix_task_execution_logs_status", "status"),
        Index("ix_task_execution_logs_started_at", "started_at"),
    )

    def __repr__(self) -> str:
        return f"<TaskExecutionLog {self.task_id}: {self.status}>"
