"""
Audit log schemas.
"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.base import PaginationParams, PaginationResponse


class AuditLogBase(BaseModel):
    """Base audit log schema."""
    operation_type: str = Field(..., max_length=50, description="操作类型: LOGIN, LOGOUT, CREATE, UPDATE, DELETE, EXPORT")
    operation_module: str = Field(..., max_length=50, description="模块: asset, user, role, monitor, certificate, deploy, system")
    object_type: str | None = Field(None, max_length=100, description="操作对象类型")
    object_id: str | None = Field(None, max_length=100, description="操作对象ID")
    object_name: str | None = Field(None, max_length=200, description="操作对象名称")
    before_data: dict[str, Any] | None = Field(None, description="操作前数据")
    after_data: dict[str, Any] | None = Field(None, description="操作后数据")
    operator_id: int | None = Field(None, description="操作人ID")
    operator_name: str | None = Field(None, max_length=100, description="操作人名称")
    operator_ip: str | None = Field(None, max_length=50, description="操作人IP")
    user_agent: str | None = Field(None, description="用户代理")
    status: str = Field(default="SUCCESS", max_length=20, description="操作状态: SUCCESS, FAILURE")
    error_message: str | None = Field(None, description="错误信息")
    request_id: str | None = Field(None, max_length=100, description="请求ID")
    duration_ms: int | None = Field(None, description="操作耗时(毫秒)")


class AuditLogCreate(AuditLogBase):
    """Audit log creation schema (internal use)."""
    operation_time: datetime = Field(default_factory=datetime.utcnow, description="操作时间")


class AuditLogResponse(AuditLogBase):
    """Audit log response schema."""
    id: int
    operation_time: datetime

    class Config:
        from_attributes = True


class AuditLogQuery(PaginationParams):
    """Audit log query parameters."""
    operator_id: int | None = Field(None, description="操作人ID")
    operation_type: str | None = Field(None, max_length=50, description="操作类型")
    operation_module: str | None = Field(None, max_length=50, description="模块")
    object_type: str | None = Field(None, max_length=100, description="对象类型")
    status: str | None = Field(None, max_length=20, description="操作状态")
    start_time: datetime | None = Field(None, description="开始时间")
    end_time: datetime | None = Field(None, description="结束时间")
    keyword: str | None = Field(None, description="关键词搜索(对象名称、操作人名称)")


class AuditLogListResponse(BaseModel):
    """Audit log list response with pagination."""
    items: list[AuditLogResponse]
    pagination: PaginationResponse
