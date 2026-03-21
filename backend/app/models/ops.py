"""
Operations management models.
"""
import enum
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class DeploymentStatus(enum.StrEnum):
    """Deployment status enum."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLBACK = "rollback"


class Deployment(BaseModel):
    """Deployment record model."""

    __tablename__ = "deployments"

    project_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    environment: Mapped[str] = mapped_column(String(50), nullable=False)  # dev, test, staging, prod
    status: Mapped[DeploymentStatus] = mapped_column(
        SQLEnum(DeploymentStatus),
        default=DeploymentStatus.PENDING,
        nullable=False
    )

    # People
    deployer_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    deployer: Mapped[Optional["User"]] = relationship("User", foreign_keys=[deployer_id], lazy="selectin")

    approver_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    approver: Mapped[Optional["User"]] = relationship("User", foreign_keys=[approver_id], lazy="selectin")

    # Timing
    deploy_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Details
    log_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    rollback_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=dict, nullable=True)

    def __repr__(self) -> str:
        return f"<Deployment {self.project_name}:{self.version}>"


class InspectionType(enum.StrEnum):
    """Inspection type enum."""
    SYSTEM = "system"
    SECURITY = "security"
    PERFORMANCE = "performance"
    CUSTOM = "custom"


class InspectionTask(BaseModel):
    """Inspection task model."""

    __tablename__ = "inspection_tasks"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    task_type: Mapped[InspectionType] = mapped_column(
        SQLEnum(InspectionType),
        default=InspectionType.SYSTEM,
        nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Schedule
    cron_expression: Mapped[str] = mapped_column(String(100), nullable=False)  # Cron format
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Targets
    target_assets: Mapped[list[int]] = mapped_column(JSON, default=list, nullable=False)
    check_items: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)

    # Execution tracking
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    reports: Mapped[list["InspectionReport"]] = relationship(
        "InspectionReport",
        back_populates="task",
        lazy="selectin",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<InspectionTask {self.name}>"


class InspectionReport(BaseModel):
    """Inspection report model."""

    __tablename__ = "inspection_reports"

    task_id: Mapped[int] = mapped_column(
        ForeignKey("inspection_tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    task: Mapped["InspectionTask"] = relationship("InspectionTask", back_populates="reports")

    status: Mapped[str] = mapped_column(String(20), default="running", nullable=False)  # running, completed, failed

    # Statistics
    total_checks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    passed_checks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_checks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    warning_checks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Results
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    details: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)

    def __repr__(self) -> str:
        return f"<InspectionReport task={self.task_id}>"


class CertificateStatus(enum.StrEnum):
    """Certificate status enum."""
    ACTIVE = "active"
    EXPIRING = "expiring"
    EXPIRED = "expired"
    REVOKED = "revoked"


class Certificate(BaseModel):
    """SSL Certificate model."""

    __tablename__ = "certificates"

    domain: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    issuer: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    serial_number: Mapped[str] = mapped_column(String(100), nullable=False)

    # Validity
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    days_until_expiry: Mapped[int] = mapped_column(Integer, nullable=False)

    # Alert configuration
    alert_threshold_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    is_auto_renewal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Certificate data (optional, encrypted in production)
    cert_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_content: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[CertificateStatus] = mapped_column(
        SQLEnum(CertificateStatus),
        default=CertificateStatus.ACTIVE,
        nullable=False
    )

    # Associated assets
    asset_ids: Mapped[list[int]] = mapped_column(JSON, default=list, nullable=False)

    def __repr__(self) -> str:
        return f"<Certificate {self.domain}>"


class DNSRecord(BaseModel):
    """DNS record model."""

    __tablename__ = "dns_records"

    domain: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    record_type: Mapped[str] = mapped_column(String(10), nullable=False)  # A, AAAA, CNAME, MX, TXT, etc.
    host: Mapped[str] = mapped_column(String(255), nullable=False)  # @, www, mail, etc.
    value: Mapped[str] = mapped_column(Text, nullable=False)

    # DNS settings
    ttl: Mapped[int] = mapped_column(Integer, default=3600, nullable=False)
    priority: Mapped[int | None] = mapped_column(Integer, nullable=True)  # For MX records

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Provider info
    provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    provider_record_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Associated assets
    asset_ids: Mapped[list[int]] = mapped_column(JSON, default=list, nullable=False)

    def __repr__(self) -> str:
        return f"<DNSRecord {self.host}.{self.domain}>"
