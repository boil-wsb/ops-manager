from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.crud.crud_notification_callback_log import notification_callback_log
from app.schemas.notification_callback_log import (
    NotificationCallbackLogListResponse,
    NotificationCallbackLogResponse,
)

router = APIRouter(prefix="/feishu", tags=["飞书通知"])


@router.get("/callback-logs", response_model=NotificationCallbackLogListResponse)
async def get_callback_logs(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    status: str | None = Query(None, description="筛选状态: success / failed"),
    notification_record_id: int | None = Query(None, description="按通知记录筛选"),
    db: AsyncSession = Depends(get_db),
):
    total, items = await notification_callback_log.get_multi(
        db,
        page=page,
        page_size=page_size,
        status=status,
        notification_record_id=notification_record_id,
    )
    return NotificationCallbackLogListResponse(
        total=total,
        items=[NotificationCallbackLogResponse.model_validate(item) for item in items],
        page=page,
        page_size=page_size,
    )
