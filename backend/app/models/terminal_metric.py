"""
Terminal Metric models - aggregated metrics for terminal assets.
"""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class TerminalMetric(BaseModel):
    """Aggregated terminal metrics for dashboard display."""

    __tablename__ = "terminal_metrics"
    __table_args__ = (
        Index("idx_owner_username", "owner_username"),
        Index("idx_asset_id", "asset_id"),
        Index("idx_current_status", "current_status"),
        Index("idx_metrics_timestamp", "metrics_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    owner_username: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    hostname: Mapped[str] = mapped_column(String(255), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)

    cpu_usage: Mapped[float | None] = mapped_column(Float, nullable=True)
    memory_usage: Mapped[float | None] = mapped_column(Float, nullable=True)
    memory_total_gb: Mapped[float | None] = mapped_column(Float, nullable=True)
    disk_usage: Mapped[float | None] = mapped_column(Float, nullable=True)
    disk_total_gb: Mapped[float | None] = mapped_column(Float, nullable=True)
    network_in: Mapped[float | None] = mapped_column(Float, nullable=True)
    network_out: Mapped[float | None] = mapped_column(Float, nullable=True)
    uptime_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)

    last_heartbeat: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    current_status: Mapped[str] = mapped_column(String(20), nullable=False, default="unknown")
    alert_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    alert_severity: Mapped[str | None] = mapped_column(String(20), nullable=True)
    monitor_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    metrics_timestamp: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    asset: Mapped["Asset"] = relationship("Asset", back_populates="terminal_metrics")

    def __repr__(self) -> str:
        return f"<TerminalMetric {self.hostname} ({self.current_status})>"
