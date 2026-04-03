"""
Alert management schemas.
"""
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


# AlertSilence schemas
class AlertSilenceBase(BaseModel):
    """Base alert silence schema."""
    name: str = Field(..., min_length=1, max_length=200)
    match_labels: dict[str, Any] = {}
    match_pattern: str | None = None
    starts_at: datetime
    ends_at: datetime
    is_active: bool = True


class AlertSilenceCreate(AlertSilenceBase):
    """Alert silence creation schema."""
    created_by: int | None = None


class AlertSilenceUpdate(BaseModel):
    """Alert silence update schema."""
    name: str | None = Field(None, min_length=1, max_length=200)
    match_labels: dict[str, Any] | None = None
    match_pattern: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    is_active: bool | None = None


class AlertSilenceResponse(AlertSilenceBase):
    """Alert silence response schema."""
    id: int
    created_by: int | None
    created_at: datetime
    updated_at: datetime


# AlertTemplate schemas
class AlertTemplateBase(BaseModel):
    """Base alert template schema."""
    model_config = ConfigDict(from_attributes=True)

    name: str = Field(..., min_length=1, max_length=200)
    template_type: str = Field(..., pattern="^(email|feishu)$")
    subject_template: str | None = None
    body_template: str | None = None
    card_config: dict[str, Any] | None = None
    is_default: bool = False
    is_active: bool = True


class AlertTemplateCreate(AlertTemplateBase):
    """Alert template creation schema."""
    pass


class AlertTemplateUpdate(BaseModel):
    """Alert template update schema."""
    model_config = ConfigDict(from_attributes=True)

    name: str | None = Field(None, min_length=1, max_length=200)
    template_type: str | None = Field(None, pattern="^(email|feishu)$")
    subject_template: str | None = None
    body_template: str | None = None
    card_config: dict[str, Any] | None = None
    is_default: bool | None = None
    is_active: bool | None = None


class AlertTemplateResponse(AlertTemplateBase):
    """Alert template response schema."""
    id: int
    created_at: datetime
    updated_at: datetime


class AlertTemplatePreview(BaseModel):
    """Alert template preview schema."""
    labels: dict[str, str] = {}
    annotations: dict[str, str] = {}


# AlertHistory schemas
AlertHistoryStatus = Literal["firing", "resolved", "suppressed"]
AlertHistorySeverity = Literal["info", "warning", "critical", "middle"]


class AlertHistoryResponse(BaseModel):
    """Alert history response schema."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    alertname: str
    status: AlertHistoryStatus
    severity: AlertHistorySeverity
    labels: dict[str, Any]
    annotations: dict[str, Any]
    starts_at: datetime
    ends_at: datetime | None
    is_suppressed: bool
    silence_id: int | None
    notification_sent: bool
    created_at: datetime


class AlertHistoryListParams(BaseModel):
    """Alert history list query parameters."""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    alertname: str | None = None
    status: str | None = Field(None, pattern="^(firing|resolved|suppressed)$")
    severity: str | None = Field(None, pattern="^(info|warning|critical)$")
    is_suppressed: bool | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None


class AlertHistoryListResponse(BaseModel):
    """Alert history list response."""
    total: int
    page: int
    page_size: int
    items: list[AlertHistoryResponse]


# Alertmanager webhook payload schemas (Alertmanager v4 format)
class AlertmanagerWebhookCommon(BaseModel):
    """Common fields for Alertmanager webhook payload."""
    version: str | None = None
    groupKey: str | None = None
    truncatedAlerts: int | None = None


class AlertmanagerAlert(BaseModel):
    """Single alert from Alertmanager webhook payload."""
    status: str | None = None
    labels: dict[str, Any] = {}
    annotations: dict[str, Any] = {}
    startsAt: datetime | None = None
    endsAt: datetime | None = None
    generatorURL: str | None = None
    fingerprint: str | None = None


class AlertmanagerWebhookPayload(BaseModel):
    """Alertmanager v4 webhook payload schema."""
    receiver: str | None = None
    status: str | None = None
    alerts: list[AlertmanagerAlert] = []
    groupLabels: dict[str, Any] = {}
    commonLabels: dict[str, Any] = {}
    commonAnnotations: dict[str, Any] = {}
    externalURL: str | None = None

    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "receiver": "webhook",
                "status": "firing",
                "alerts": [
                    {
                        "status": "firing",
                        "labels": {
                            "alertname": "HighMemoryUsage",
                            "severity": "critical",
                            "instance": "server-01"
                        },
                        "annotations": {
                            "summary": "High memory usage detected",
                            "description": "Memory usage is above 90%"
                        },
                        "startsAt": "2024-01-01T00:00:00Z",
                        "endsAt": "0001-01-01T00:00:00Z",
                        "generatorURL": "http://prometheus:9090/graph?..."
                    }
                ],
                "groupLabels": {"alertname": "HighMemoryUsage"},
                "commonLabels": {"severity": "critical"},
                "commonAnnotations": {"summary": "High memory usage detected"},
                "externalURL": "http://alertmanager:9093"
            }
        }
