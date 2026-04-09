"""
Operations management schemas.
"""

from datetime import datetime

from pydantic import BaseModel, Field


# Deployment schemas
class DeploymentBase(BaseModel):
    """Base deployment schema."""

    project_name: str = Field(..., min_length=1, max_length=100)
    version: str = Field(..., min_length=1, max_length=50)
    environment: str = Field(..., pattern="^(dev|test|staging|prod)$")


class DeploymentCreate(DeploymentBase):
    """Deployment creation schema."""

    pass


class DeploymentUpdate(BaseModel):
    """Deployment update schema."""

    status: str | None = Field(None, pattern="^(pending|running|success|failed|rollback)$")
    log_output: str | None = None
    rollback_reason: str | None = None
    duration_seconds: int | None = None


class DeploymentResponse(DeploymentBase):
    """Deployment response schema."""

    id: int
    status: str
    deployer_id: int | None
    deployer_name: str | None
    approver_id: int | None
    approver_name: str | None
    deploy_time: datetime | None
    duration_seconds: int | None
    rollback_reason: str | None
    created_at: datetime


class DeploymentListResponse(BaseModel):
    """Deployment list response."""

    total: int
    items: list[DeploymentResponse]


# Inspection schemas
class InspectionCheckItem(BaseModel):
    """Inspection check item."""

    name: str
    command: str | None = None
    expected_result: str | None = None
    timeout: int = 60


class InspectionTaskBase(BaseModel):
    """Base inspection task schema."""

    name: str = Field(..., min_length=1, max_length=200)
    task_type: str = Field(default="system", pattern="^(system|security|performance|custom)$")
    description: str | None = None
    cron_expression: str = Field(..., min_length=1, max_length=100)
    target_assets: list[int] = []
    check_items: list[InspectionCheckItem] = []


class InspectionTaskCreate(InspectionTaskBase):
    """Inspection task creation schema."""

    pass


class InspectionTaskUpdate(BaseModel):
    """Inspection task update schema."""

    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    cron_expression: str | None = Field(None, min_length=1, max_length=100)
    is_enabled: bool | None = None
    target_assets: list[int] | None = None
    check_items: list[InspectionCheckItem] | None = None


class InspectionTaskResponse(InspectionTaskBase):
    """Inspection task response schema."""

    id: int
    is_enabled: bool
    last_run_at: datetime | None
    next_run_at: datetime | None
    created_at: datetime
    updated_at: datetime


class InspectionReportDetail(BaseModel):
    """Inspection report detail item."""

    check_name: str
    status: str  # passed, failed, warning
    message: str | None = None
    duration_ms: int | None = None


class InspectionReportResponse(BaseModel):
    """Inspection report response schema."""

    id: int
    task_id: int
    task_name: str
    status: str
    total_checks: int
    passed_checks: int
    failed_checks: int
    warning_checks: int
    summary: str | None
    details: list[InspectionReportDetail]
    created_at: datetime


# Certificate schemas
class CertificateBase(BaseModel):
    """Base certificate schema."""

    domain: str = Field(..., min_length=1, max_length=255)
    issuer: str = Field(..., min_length=1, max_length=255)
    subject: str = Field(..., min_length=1, max_length=255)
    serial_number: str = Field(..., min_length=1, max_length=100)
    valid_from: datetime
    valid_until: datetime


class CertificateCreate(CertificateBase):
    """Certificate creation schema."""

    alert_threshold_days: int = 30
    is_auto_renewal: bool = False
    cert_content: str | None = None
    key_content: str | None = None
    asset_ids: list[int] = []


class CertificateUpdate(BaseModel):
    """Certificate update schema."""

    alert_threshold_days: int | None = None
    is_auto_renewal: bool | None = None
    cert_content: str | None = None
    key_content: str | None = None
    asset_ids: list[int] | None = None
    status: str | None = Field(None, pattern="^(active|expiring|expired|revoked)$")


class CertificateResponse(CertificateBase):
    """Certificate response schema."""

    id: int
    days_until_expiry: int
    alert_threshold_days: int
    is_auto_renewal: bool
    status: str
    asset_ids: list[int]
    created_at: datetime
    updated_at: datetime


class CertificateSyncResponse(BaseModel):
    """Certificate sync response schema."""

    total: int
    created: int
    updated: int
    certificates: list[CertificateResponse]


# DNS schemas
class DNSRecordBase(BaseModel):
    """Base DNS record schema."""

    domain: str = Field(..., min_length=1, max_length=255)
    record_type: str = Field(..., pattern="^(A|AAAA|CNAME|MX|TXT|NS|SRV|PTR|CAA)$")
    host: str = Field(..., min_length=1, max_length=255)
    value: str = Field(..., min_length=1)
    ttl: int = Field(default=3600, ge=60)
    priority: int | None = Field(None, ge=0, le=65535)


class DNSRecordCreate(DNSRecordBase):
    """DNS record creation schema."""

    provider: str | None = None
    asset_ids: list[int] = []


class DNSRecordUpdate(BaseModel):
    """DNS record update schema."""

    value: str | None = Field(None, min_length=1)
    ttl: int | None = Field(None, ge=60)
    priority: int | None = Field(None, ge=0, le=65535)
    is_active: bool | None = None
    asset_ids: list[int] | None = None


class DNSRecordResponse(DNSRecordBase):
    """DNS record response schema."""

    id: int
    is_active: bool
    provider: str | None
    asset_ids: list[int]
    created_at: datetime
    updated_at: datetime
