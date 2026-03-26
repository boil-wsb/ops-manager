"""
Monitoring and alerting schemas.
"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# Monitor schemas
class MonitorBase(BaseModel):
    """Base monitor schema."""
    name: str = Field(..., min_length=1, max_length=200)
    monitor_type: str = Field(..., pattern="^(ping|http|tcp|udp)$")
    target: str = Field(..., min_length=1, max_length=500)

    interval_seconds: int = Field(default=60, ge=10)
    timeout_seconds: int = Field(default=10, ge=1)
    retry_count: int = Field(default=3, ge=1)

    # HTTP specific
    http_method: str | None = Field(None, pattern="^(GET|POST|PUT|DELETE|HEAD|OPTIONS|PATCH)$")
    http_headers: dict[str, str] | None = None
    http_body: str | None = None
    expected_status_code: int | None = Field(None, ge=100, le=599)
    expected_response_content: str | None = None

    # Thresholds
    threshold_warning: float | None = None
    threshold_critical: float | None = None


class MonitorCreate(MonitorBase):
    """Monitor creation schema."""
    asset_id: int | None = None


class MonitorUpdate(BaseModel):
    """Monitor update schema."""
    name: str | None = Field(None, min_length=1, max_length=200)
    target: str | None = Field(None, min_length=1, max_length=500)
    interval_seconds: int | None = Field(None, ge=10)
    timeout_seconds: int | None = Field(None, ge=1)
    retry_count: int | None = Field(None, ge=1)
    http_method: str | None = None
    http_headers: dict[str, str] | None = None
    expected_status_code: int | None = Field(None, ge=100, le=599)
    threshold_warning: float | None = None
    threshold_critical: float | None = None
    is_enabled: bool | None = None
    asset_id: int | None = None


class MonitorResponse(MonitorBase):
    """Monitor response schema."""
    id: int
    is_enabled: bool
    current_status: str
    last_check_at: datetime | None
    last_check_result: str | None
    last_check_duration_ms: int | None
    asset_id: int | None
    created_at: datetime
    updated_at: datetime


class MonitorListResponse(BaseModel):
    """Monitor list response."""
    total: int
    items: list[MonitorResponse]


# Alert schemas
class AlertBase(BaseModel):
    """Base alert schema."""
    title: str = Field(..., min_length=1, max_length=500)
    message: str | None = None
    severity: str = Field(default="warning", pattern="^(info|warning|critical)$")


class AlertCreate(AlertBase):
    """Alert creation schema."""
    monitor_id: int
    alert_rule_id: int | None = None
    metric_name: str | None = None
    metric_value: float | None = None
    threshold_value: float | None = None


class AlertResponse(AlertBase):
    """Alert response schema."""
    id: int
    monitor_id: int
    monitor_name: str
    alert_rule_id: int | None
    status: str
    metric_name: str | None
    metric_value: float | None
    threshold_value: float | None
    started_at: datetime
    acknowledged_at: datetime | None
    acknowledged_by: int | None
    resolved_at: datetime | None
    resolved_by: int | None
    notification_sent: bool


class AlertAction(BaseModel):
    """Alert action schema."""
    action: str = Field(..., pattern="^(acknowledge|resolve|suppress)$")
    comment: str | None = None


class AlertListResponse(BaseModel):
    """Alert list response."""
    total: int
    items: list[AlertResponse]


# Alert rule schemas
class AlertRuleBase(BaseModel):
    """Base alert rule schema."""
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    condition_expression: str = Field(..., min_length=1)
    duration_seconds: int = Field(default=0, ge=0)
    severity: str = Field(default="warning", pattern="^(info|warning|critical)$")
    notification_channels: list[str] = []


class AlertRuleCreate(AlertRuleBase):
    """Alert rule creation schema."""
    notification_template: str | None = None
    suppress_interval_minutes: int = 0


class AlertRuleUpdate(BaseModel):
    """Alert rule update schema."""
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    condition_expression: str | None = None
    duration_seconds: int | None = Field(None, ge=0)
    severity: str | None = Field(None, pattern="^(info|warning|critical)$")
    notification_channels: list[str] | None = None
    is_enabled: bool | None = None


class AlertRuleResponse(AlertRuleBase):
    """Alert rule response schema."""
    id: int
    notification_template: str | None
    suppress_interval_minutes: int
    is_enabled: bool
    created_at: datetime
    updated_at: datetime


# Notification channel schemas
class NotificationChannelBase(BaseModel):
    """Base notification channel schema."""
    name: str = Field(..., min_length=1, max_length=100)
    channel_type: str = Field(..., pattern="^(email|webhook|sms)$")


class NotificationChannelCreate(NotificationChannelBase):
    """Notification channel creation schema."""
    config: dict[str, Any] = {}


class NotificationChannelUpdate(BaseModel):
    """Notification channel update schema."""
    name: str | None = Field(None, min_length=1, max_length=100)
    config: dict[str, Any] | None = None
    is_enabled: bool | None = None


class NotificationChannelResponse(NotificationChannelBase):
    """Notification channel response schema."""
    id: int
    config: dict[str, Any]
    is_enabled: bool
    last_test_at: datetime | None
    last_test_status: str | None
    created_at: datetime
    updated_at: datetime


class MonitorTerminalResponse(BaseModel):
    """Monitor terminal response schema for user's terminals."""
    id: int
    name: str
    asset_id: str
    ip_address: str | None
    hostname: str | None
    owner_name: str | None
    current_status: str
    last_check_at: datetime | None
    monitor_id: int | None = None
    monitor_name: str | None = None


class MonitorTerminalListResponse(BaseModel):
    """Monitor terminal list response with pagination."""
    total: int
    items: list[MonitorTerminalResponse]
