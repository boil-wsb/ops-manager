"""
Monitoring and alerting schemas.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
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
    http_method: Optional[str] = Field(None, pattern="^(GET|POST|PUT|DELETE|HEAD|OPTIONS|PATCH)$")
    http_headers: Optional[Dict[str, str]] = None
    http_body: Optional[str] = None
    expected_status_code: Optional[int] = Field(None, ge=100, le=599)
    expected_response_content: Optional[str] = None
    
    # Thresholds
    threshold_warning: Optional[float] = None
    threshold_critical: Optional[float] = None


class MonitorCreate(MonitorBase):
    """Monitor creation schema."""
    asset_id: Optional[int] = None


class MonitorUpdate(BaseModel):
    """Monitor update schema."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    target: Optional[str] = Field(None, min_length=1, max_length=500)
    interval_seconds: Optional[int] = Field(None, ge=10)
    timeout_seconds: Optional[int] = Field(None, ge=1)
    retry_count: Optional[int] = Field(None, ge=1)
    http_method: Optional[str] = None
    http_headers: Optional[Dict[str, str]] = None
    expected_status_code: Optional[int] = Field(None, ge=100, le=599)
    threshold_warning: Optional[float] = None
    threshold_critical: Optional[float] = None
    is_enabled: Optional[bool] = None
    asset_id: Optional[int] = None


class MonitorResponse(MonitorBase):
    """Monitor response schema."""
    id: int
    is_enabled: bool
    current_status: str
    last_check_at: Optional[datetime]
    last_check_result: Optional[str]
    last_check_duration_ms: Optional[int]
    asset_id: Optional[int]
    created_at: datetime
    updated_at: datetime


class MonitorListResponse(BaseModel):
    """Monitor list response."""
    total: int
    items: List[MonitorResponse]


# Alert schemas
class AlertBase(BaseModel):
    """Base alert schema."""
    title: str = Field(..., min_length=1, max_length=500)
    message: Optional[str] = None
    severity: str = Field(default="warning", pattern="^(info|warning|critical)$")


class AlertCreate(AlertBase):
    """Alert creation schema."""
    monitor_id: int
    alert_rule_id: Optional[int] = None
    metric_name: Optional[str] = None
    metric_value: Optional[float] = None
    threshold_value: Optional[float] = None


class AlertResponse(AlertBase):
    """Alert response schema."""
    id: int
    monitor_id: int
    monitor_name: str
    alert_rule_id: Optional[int]
    status: str
    metric_name: Optional[str]
    metric_value: Optional[float]
    threshold_value: Optional[float]
    started_at: datetime
    acknowledged_at: Optional[datetime]
    acknowledged_by: Optional[int]
    resolved_at: Optional[datetime]
    resolved_by: Optional[int]
    notification_sent: bool


class AlertAction(BaseModel):
    """Alert action schema."""
    action: str = Field(..., pattern="^(acknowledge|resolve|suppress)$")
    comment: Optional[str] = None


class AlertListResponse(BaseModel):
    """Alert list response."""
    total: int
    items: List[AlertResponse]


# Alert rule schemas
class AlertRuleBase(BaseModel):
    """Base alert rule schema."""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    condition_expression: str = Field(..., min_length=1)
    duration_seconds: int = Field(default=0, ge=0)
    severity: str = Field(default="warning", pattern="^(info|warning|critical)$")
    notification_channels: List[str] = []


class AlertRuleCreate(AlertRuleBase):
    """Alert rule creation schema."""
    notification_template: Optional[str] = None
    suppress_interval_minutes: int = 0


class AlertRuleUpdate(BaseModel):
    """Alert rule update schema."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    condition_expression: Optional[str] = None
    duration_seconds: Optional[int] = Field(None, ge=0)
    severity: Optional[str] = Field(None, pattern="^(info|warning|critical)$")
    notification_channels: Optional[List[str]] = None
    is_enabled: Optional[bool] = None


class AlertRuleResponse(AlertRuleBase):
    """Alert rule response schema."""
    id: int
    notification_template: Optional[str]
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
    config: Dict[str, Any] = {}


class NotificationChannelUpdate(BaseModel):
    """Notification channel update schema."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    config: Optional[Dict[str, Any]] = None
    is_enabled: Optional[bool] = None


class NotificationChannelResponse(NotificationChannelBase):
    """Notification channel response schema."""
    id: int
    config: Dict[str, Any]
    is_enabled: bool
    last_test_at: Optional[datetime]
    last_test_status: Optional[str]
    created_at: datetime
    updated_at: datetime
