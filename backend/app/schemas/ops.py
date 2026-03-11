"""
Operations management schemas.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
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
    status: Optional[str] = Field(None, pattern="^(pending|running|success|failed|rollback)$")
    log_output: Optional[str] = None
    rollback_reason: Optional[str] = None
    duration_seconds: Optional[int] = None


class DeploymentResponse(DeploymentBase):
    """Deployment response schema."""
    id: int
    status: str
    deployer_id: Optional[int]
    deployer_name: Optional[str]
    approver_id: Optional[int]
    approver_name: Optional[str]
    deploy_time: Optional[datetime]
    duration_seconds: Optional[int]
    rollback_reason: Optional[str]
    created_at: datetime


class DeploymentListResponse(BaseModel):
    """Deployment list response."""
    total: int
    items: List[DeploymentResponse]


# Inspection schemas
class InspectionCheckItem(BaseModel):
    """Inspection check item."""
    name: str
    command: Optional[str] = None
    expected_result: Optional[str] = None
    timeout: int = 60


class InspectionTaskBase(BaseModel):
    """Base inspection task schema."""
    name: str = Field(..., min_length=1, max_length=200)
    task_type: str = Field(default="system", pattern="^(system|security|performance|custom)$")
    description: Optional[str] = None
    cron_expression: str = Field(..., min_length=1, max_length=100)
    target_assets: List[int] = []
    check_items: List[InspectionCheckItem] = []


class InspectionTaskCreate(InspectionTaskBase):
    """Inspection task creation schema."""
    pass


class InspectionTaskUpdate(BaseModel):
    """Inspection task update schema."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    cron_expression: Optional[str] = Field(None, min_length=1, max_length=100)
    is_enabled: Optional[bool] = None
    target_assets: Optional[List[int]] = None
    check_items: Optional[List[InspectionCheckItem]] = None


class InspectionTaskResponse(InspectionTaskBase):
    """Inspection task response schema."""
    id: int
    is_enabled: bool
    last_run_at: Optional[datetime]
    next_run_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class InspectionReportDetail(BaseModel):
    """Inspection report detail item."""
    check_name: str
    status: str  # passed, failed, warning
    message: Optional[str] = None
    duration_ms: Optional[int] = None


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
    summary: Optional[str]
    details: List[InspectionReportDetail]
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
    cert_content: Optional[str] = None
    key_content: Optional[str] = None
    asset_ids: List[int] = []


class CertificateUpdate(BaseModel):
    """Certificate update schema."""
    alert_threshold_days: Optional[int] = None
    is_auto_renewal: Optional[bool] = None
    cert_content: Optional[str] = None
    key_content: Optional[str] = None
    asset_ids: Optional[List[int]] = None
    status: Optional[str] = Field(None, pattern="^(active|expiring|expired|revoked)$")


class CertificateResponse(CertificateBase):
    """Certificate response schema."""
    id: int
    days_until_expiry: int
    alert_threshold_days: int
    is_auto_renewal: bool
    status: str
    asset_ids: List[int]
    created_at: datetime
    updated_at: datetime


# DNS schemas
class DNSRecordBase(BaseModel):
    """Base DNS record schema."""
    domain: str = Field(..., min_length=1, max_length=255)
    record_type: str = Field(..., pattern="^(A|AAAA|CNAME|MX|TXT|NS|SRV|PTR|CAA)$")
    host: str = Field(..., min_length=1, max_length=255)
    value: str = Field(..., min_length=1)
    ttl: int = Field(default=3600, ge=60)
    priority: Optional[int] = Field(None, ge=0, le=65535)


class DNSRecordCreate(DNSRecordBase):
    """DNS record creation schema."""
    provider: Optional[str] = None
    asset_ids: List[int] = []


class DNSRecordUpdate(BaseModel):
    """DNS record update schema."""
    value: Optional[str] = Field(None, min_length=1)
    ttl: Optional[int] = Field(None, ge=60)
    priority: Optional[int] = Field(None, ge=0, le=65535)
    is_active: Optional[bool] = None
    asset_ids: Optional[List[int]] = None


class DNSRecordResponse(DNSRecordBase):
    """DNS record response schema."""
    id: int
    is_active: bool
    provider: Optional[str]
    asset_ids: List[int]
    created_at: datetime
    updated_at: datetime
