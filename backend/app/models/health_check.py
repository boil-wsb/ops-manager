"""Health check models."""

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class HealthCheckReport(BaseModel):
    """Health check report model."""

    __tablename__ = "health_check_reports"

    report_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source: Mapped[str] = mapped_column(String(50), default="prometheus")
    total_hosts: Mapped[int] = mapped_column(Integer, default=0)
    ok_count: Mapped[int] = mapped_column(Integer, default=0)
    warning_count: Mapped[int] = mapped_column(Integer, default=0)
    critical_count: Mapped[int] = mapped_column(Integer, default=0)
    notification_sent: Mapped[bool] = mapped_column(Boolean, default=False)

    details: Mapped[list["HealthCheckDetail"]] = relationship(
        "HealthCheckDetail", back_populates="report", lazy="selectin", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<HealthCheckReport {self.report_time}>"


class HealthCheckDetail(BaseModel):
    """Health check detail model."""

    __tablename__ = "health_check_details"

    report_id: Mapped[int] = mapped_column(
        ForeignKey("health_check_reports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    report: Mapped["HealthCheckReport"] = relationship(
        "HealthCheckReport", back_populates="details"
    )

    instance: Mapped[str] = mapped_column(String(255))
    asset_type: Mapped[str] = mapped_column(String(50))  # "server" / "terminal"
    host_status: Mapped[str] = mapped_column(String(20))  # "ok" / "warning" / "critical"
    env: Mapped[str | None] = mapped_column(String(50), nullable=True)

    os_info: Mapped[str | None] = mapped_column(String(255), nullable=True)
    kernel_version: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cpu_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cpu_usage: Mapped[float | None] = mapped_column(Float, nullable=True)
    load1: Mapped[float | None] = mapped_column(Float, nullable=True)
    load5: Mapped[float | None] = mapped_column(Float, nullable=True)
    load15: Mapped[float | None] = mapped_column(Float, nullable=True)
    memory_usage: Mapped[float | None] = mapped_column(Float, nullable=True)
    memory_total_mb: Mapped[float | None] = mapped_column(Float, nullable=True)
    memory_used_mb: Mapped[float | None] = mapped_column(Float, nullable=True)
    disk_usage: Mapped[float | None] = mapped_column(Float, nullable=True)
    disk_total_gb: Mapped[float | None] = mapped_column(Float, nullable=True)

    is_online: Mapped[bool] = mapped_column(Boolean, default=True)
    check_details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    def __repr__(self) -> str:
        return f"<HealthCheckDetail {self.instance}>"
