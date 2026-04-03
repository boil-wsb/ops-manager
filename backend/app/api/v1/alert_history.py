"""
Alert history API routes.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.exceptions import NotFoundError
from app.crud.crud_alert import crud_alert_history
from app.schemas.alert import AlertHistoryResponse, AlertHistoryListParams, AlertHistoryListResponse

router = APIRouter()


@router.get("/history")
async def get_alert_history(
    params: AlertHistoryListParams = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Get alert history with filtering and pagination."""
    skip = (params.page - 1) * params.page_size
    items, total = await crud_alert_history.get_multi_with_filters(
        db,
        skip=skip,
        limit=params.page_size,
        alertname=params.alertname,
        status=params.status,
        start_time=params.start_time,
        end_time=params.end_time,
    )
    return AlertHistoryListResponse(
        total=total,
        page=params.page,
        page_size=params.page_size,
        items=[AlertHistoryResponse.model_validate(item) for item in items]
    )


@router.get("/history/{history_id}", response_model=AlertHistoryResponse)
async def get_alert_history_detail(
    history_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific alert history record."""
    history = await crud_alert_history.get(db, id=history_id)
    if not history:
        raise NotFoundError(detail=f"Alert history with ID {history_id} not found")
    return history
