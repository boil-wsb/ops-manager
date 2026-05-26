"""
Notification Record API endpoints.
"""

from app.core.logging import get_logger

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.crud.crud_notification_record import notification_record
from app.schemas.notification_record import (
    NotificationRecordListResponse,
    NotificationRecordResponse,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/notification-records", tags=["通知记录"])


@router.get("", response_model=NotificationRecordListResponse)
async def list_notification_records(
    page: int = Query(1, ge=1, le=100),
    page_size: int = Query(10, ge=10, le=100),
    user: str | None = None,
    success: bool | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List notification records with pagination and filtering."""
    skip = (page - 1) * page_size
    total, items = await notification_record.get_multi(
        db,
        skip=skip,
        limit=page_size,
        user=user,
        success=success,
    )
    return NotificationRecordListResponse(
        total=total,
        items=[NotificationRecordResponse.model_validate(item) for item in items],
    )


@router.get("/{record_id}", response_model=NotificationRecordResponse)
async def get_notification_record(
    record_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a single notification record by ID."""
    record = await notification_record.get(db, record_id)
    if not record:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Notification record not found")
    return NotificationRecordResponse.model_validate(record)


@router.delete("/{record_id}")
async def delete_notification_record(
    record_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a notification record."""
    success = await notification_record.delete(db, record_id=record_id)
    if not success:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Notification record not found")
    return {"message": "Notification record deleted successfully"}
