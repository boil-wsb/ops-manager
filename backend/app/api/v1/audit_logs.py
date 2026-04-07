"""
Audit log API routes.
"""
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.exceptions import NotFoundError
from app.crud.audit_log import crud_audit_log
from app.schemas.audit_log import AuditLogListResponse, AuditLogResponse

router = APIRouter()


@router.get("/audit-logs", response_model=AuditLogListResponse)
async def list_audit_logs(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    operator_id: int | None = Query(None, description="操作人ID"),
    operation_type: str | None = Query(
        None, description="操作类型: LOGIN, LOGOUT, CREATE, UPDATE, DELETE, EXPORT"
    ),
    operation_module: str | None = Query(
        None, description="模块: asset, user, role, monitor, certificate, deploy, system"
    ),
    object_type: str | None = Query(None, description="对象类型"),
    status: str | None = Query(None, description="操作状态: SUCCESS, FAILURE"),
    start_time: datetime | None = Query(None, description="开始时间 (ISO 8601格式)"),
    end_time: datetime | None = Query(None, description="结束时间 (ISO 8601格式)"),
    keyword: str | None = Query(None, description="关键词搜索(对象名称、操作人名称)"),
    db: AsyncSession = Depends(get_db),
):
    """查询审计日志列表。

    支持分页、筛选、时间范围和关键字搜索。
    """
    skip = (page - 1) * page_size

    items, total = await crud_audit_log.get_multi_with_filters(
        db,
        skip=skip,
        limit=page_size,
        operator_id=operator_id,
        operation_type=operation_type,
        operation_module=operation_module,
        object_type=object_type,
        status=status,
        start_time=start_time,
        end_time=end_time,
        keyword=keyword,
    )

    pages = (total + page_size - 1) // page_size

    return AuditLogListResponse(
        items=list(items),
        pagination={
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages,
        },
    )


@router.get("/audit-logs/{log_id}", response_model=AuditLogResponse)
async def get_audit_log(
    log_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取单条审计日志详情。"""
    audit_log = await crud_audit_log.get_by_id(db, log_id=log_id)
    if not audit_log:
        raise NotFoundError(detail=f"Audit log with ID {log_id} not found")
    return audit_log
