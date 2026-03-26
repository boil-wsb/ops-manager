"""
IT Feedback API endpoints.
"""
from contextlib import suppress
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.it_feedback import ITFeedback
from app.schemas.it_feedback import (
    ITFeedbackCreate,
    ITFeedbackListResponse,
    ITFeedbackResponse,
)


def get_feishu_service():
    """Lazy import FeishuService."""
    from app.integrations.feishu.service import get_feishu_service as _get
    return _get()


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    if request.client:
        return request.client.host
    return "unknown"


router = APIRouter(prefix="/it-feedback")


@router.post("", response_model=ITFeedbackResponse)
async def create_feedback(
    feedback_in: ITFeedbackCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    client_ip = get_client_ip(request)
    feedback = ITFeedback(
        computer_type=feedback_in.computer_type,
        usage_years=feedback_in.usage_years,
        lag_level=feedback_in.lag_level,
        lag_scenarios=feedback_in.lag_scenarios,
        description=feedback_in.description,
        contact=feedback_in.contact,
        client_ip=client_ip,
        status=feedback_in.status,
    )
    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)

    from app.models.asset import Asset, AssetType

    result = await db.execute(
        select(Asset).where(
            Asset.ip_address == client_ip,
            Asset.asset_type == AssetType.TERMINAL
        )
    )
    asset = result.scalar_one_or_none()

    if asset:
        background_tasks.add_task(
            send_it_feedback_created_notification,
            user_id="ou_e7e3a761a4bc2e3ae17402c67d7685ae",
            feedback_id=feedback.id,
            client_ip=client_ip,
            asset_name=asset.name,
            description=feedback_in.description,
            contact=feedback_in.contact,
        )

    return ITFeedbackResponse.model_validate(feedback)


@router.get("", response_model=ITFeedbackListResponse)
async def list_feedback(
    status: str | None = None,
    lag_level: str | None = None,
    page: int = Query(1, ge=1, le=100),
    page_size: int = Query(10, ge=10, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(ITFeedback)

    if status:
        query = query.where(ITFeedback.status == status)
    if lag_level:
        query = query.where(ITFeedback.lag_level == lag_level)

    query = query.order_by(ITFeedback.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    total_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(total_query)).scalar() or 0

    items = (await db.execute(query)).scalars().all()

    return ITFeedbackListResponse(
        total=total,
        items=[ITFeedbackResponse.model_validate(item) for item in items],
    )


@router.get("/{feedback_id}", response_model=ITFeedbackResponse)
async def get_feedback(
    feedback_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ITFeedback).where(ITFeedback.id == feedback_id)
    )
    feedback = result.scalar_one_or_none()

    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")

    return ITFeedbackResponse.model_validate(feedback)


def send_it_feedback_created_notification(
    user_id: str,
    feedback_id: int,
    client_ip: str,
    asset_name: str | None,
    description: str | None,
    contact: str | None,
) -> None:
    """发送新IT反馈创建通知"""
    try:
        tags = [
            {"label": "反馈ID", "value": str(feedback_id)},
            {"label": "终端IP", "value": client_ip},
            {"label": "终端名称", "value": asset_name or "未知"},
            {"label": "反馈内容", "value": description or "无"},
        ]
        if contact:
            tags.append({"label": "联系方式", "value": contact})

        get_feishu_service().send_interactive_message(
            user_id=user_id,
            title="【IT反馈处理通知】",
            content="**新IT反馈待处理**",
            tags=tags,
        )
    except Exception:
        pass


def send_it_feedback_notification(
    user_id: str,
    feedback_id: int,
    feedback_content: str,
    resolved_by: str,
    notes: str | None = None,
) -> None:
    with suppress(Exception):
        get_feishu_service().send_it_feedback_resolved(
            user_id=user_id,
            feedback_id=feedback_id,
            feedback_content=feedback_content,
            resolved_by=resolved_by,
            notes=notes,
        )


@router.put("/{feedback_id}/resolve")
async def resolve_feedback(
    feedback_id: int,
    background_tasks: BackgroundTasks,
    resolved_by: str,
    notes: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ITFeedback).where(ITFeedback.id == feedback_id)
    )
    feedback = result.scalar_one_or_none()

    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")

    feedback.status = "resolved"
    feedback.resolved_at = datetime.utcnow()
    feedback.resolved_by = resolved_by
    if notes:
        feedback.notes = notes

    await db.commit()
    await db.refresh(feedback)

    background_tasks.add_task(
        send_it_feedback_notification,
        user_id="ou_e7e3a761a4bc2e3ae17402c67d7685ae",
        feedback_id=feedback_id,
        feedback_content=feedback.description or "",
        resolved_by=resolved_by,
        notes=notes,
    )

    return ITFeedbackResponse.model_validate(feedback)


@router.delete("/{feedback_id}")
async def delete_feedback(
    feedback_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ITFeedback).where(ITFeedback.id == feedback_id)
    )
    feedback = result.scalar_one_or_none()

    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")

    await db.delete(feedback)
    await db.commit()

    return {"message": "Feedback deleted successfully"}
