"""
IT Feedback API endpoints.
"""
import logging
from contextlib import suppress
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.crud.crud_notification_group import notification_group
from app.models.it_feedback import ITFeedback
from app.schemas.it_feedback import (
    ITFeedbackCreate,
    ITFeedbackListResponse,
    ITFeedbackResponse,
)

NOTIFICATION_TYPE_IT_FEEDBACK_CREATED = "it_feedback_created"
NOTIFICATION_TYPE_IT_FEEDBACK_RESOLVED = "it_feedback_resolved"

logger = logging.getLogger(__name__)


def get_feishu_service():
    """Lazy import FeishuService."""
    from app.integrations.feishu.service import get_feishu_service as _get
    return _get()


async def get_notification_user_ids(db: AsyncSession, notification_type: str) -> list[str]:
    """Get feishu open_ids from active notification group for given type."""
    groups = await notification_group.get_by_notification_type(db, notification_type)
    user_ids = []
    for group in groups:
        ids = await notification_group.get_group_member_feishu_ids(db, group.id)
        user_ids.extend(ids)
    return list(set(user_ids))


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

    local_ip_mapping = {
        "127.0.0.1": "192.168.113.120",
        "localhost": "192.168.113.120",
    }
    lookup_ip = local_ip_mapping.get(client_ip, client_ip)

    result = await db.execute(
        select(Asset).where(
            Asset.ip_address == lookup_ip,
            Asset.asset_type == AssetType.TERMINAL
        )
    )
    asset = result.scalar_one_or_none()

    if asset:
        responsible_name = None
        if hasattr(asset, 'responsible') and asset.responsible:
            responsible_name = getattr(asset.responsible, 'name', None) or getattr(asset.responsible, 'username', None)

        notification_user_ids = await get_notification_user_ids(db, NOTIFICATION_TYPE_IT_FEEDBACK_CREATED)
        open_msg_ids = []
        logger.info(f"[IT Feedback] Sending notifications to {len(notification_user_ids)} users: {notification_user_ids}")
        for user_id in notification_user_ids:
            open_msg_id = send_it_feedback_created_notification(
                user_id=user_id,
                feedback_id=feedback.id,
                client_ip=client_ip,
                asset_name=asset.name,
                description=feedback_in.description,
                contact=feedback_in.contact,
                responsible_name=responsible_name,
            )
            if open_msg_id:
                open_msg_ids.append(open_msg_id)
        if open_msg_ids:
            feedback.open_message_id = open_msg_ids[0]
            await db.commit()
            await db.refresh(feedback)
            logger.info(f"[IT Feedback] Saved open_message_id={open_msg_ids[0]} for feedback {feedback.id}, sent to {len(open_msg_ids)} users")

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
    responsible_name: str | None,
) -> str | None:
    """发送新IT反馈创建通知，返回open_message_id"""
    try:
        tags = [
            {"label": "负责人", "value": responsible_name or "待分配"},
            {"label": "终端IP", "value": client_ip},
            {"label": "终端名称", "value": asset_name or "未知"},
            {"label": "反馈内容", "value": description or "无"},
        ]
        if contact:
            tags.append({"label": "联系方式", "value": contact})

        buttons = [
            {"text": "🔧 处理", "value": f"handle_{feedback_id}", "width": "fill", "type": "primary"},
        ]

        jump_url = f"http://192.168.23.36:8080/ops/it-management?feedback_id={feedback_id}&action=handle"

        result = get_feishu_service().send_interactive_message(
            user_id=user_id,
            title="【终端卡顿 IT 反馈】",
            content="",
            tags=tags,
            buttons=buttons,
            jump_url=jump_url,
            header_template="orange",
        )
        open_message_id = result.get("message_id") if isinstance(result, dict) else None
        if open_message_id:
            logger.info(f"[IT Feedback] Notification sent to user_id={user_id}, message_id={open_message_id}")
        return open_message_id
    except Exception as e:
        logger.error(f"[IT Feedback] Failed to send notification to user_id={user_id}: {e}")
        return None


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


async def send_it_feedback_notification_task(
    notification_type: str,
    feedback_id: int,
    feedback_content: str,
    resolved_by: str,
    notes: str | None = None,
) -> None:
    """Send notification to all users in notification group (async, for background tasks)."""
    from app.db.session import get_async_session_local

    async with await get_async_session_local() as db:
        user_ids = await get_notification_user_ids(db, notification_type)
        for user_id in user_ids:
            send_it_feedback_notification(
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
        send_it_feedback_notification_task,
        notification_type=NOTIFICATION_TYPE_IT_FEEDBACK_RESOLVED,
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
