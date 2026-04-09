"""
Feishu notification API endpoints.
"""
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.crud.crud_notification_record import notification_record
from app.crud.crud_user import crud_user
from app.models.user import User
from app.schemas.notification_record import (
    NotificationRecordCreate,
    NotificationRecordUpdate,
)

logger = logging.getLogger(__name__)


def get_feishu_service():
    """Lazy import FeishuService."""
    from app.integrations.feishu.service import get_feishu_service as _get
    return _get()


router = APIRouter(prefix="/feishu", tags=["飞书通知"])


class FeishuCardSendRequest(BaseModel):
    """Request schema for sending Feishu card notification."""
    card_content: dict[str, Any] = Field(..., description="飞书卡片 JSON 内容")
    user: str = Field(..., description="要匹配的用户名或 full_name")


class FeishuCardSendResponse(BaseModel):
    """Response schema for Feishu card notification."""
    success: bool
    message_id: str | None = None
    matched_user: str | None = None
    error: str | None = None


async def _get_user_by_identifier(db: AsyncSession, identifier: str) -> User | None:
    """Get user by username first, then by full_name with feishu_open_id.

    When multiple users share the same full_name, prefer the one with feishu_open_id.
    """
    user = await crud_user.get_by_username(db, username=identifier)
    if user:
        return user

    result = await db.execute(
        select(User).where(
            and_(
                User.full_name == identifier,
                User.feishu_open_id.isnot(None)
            )
        ).limit(1)
    )
    return result.scalar_one_or_none()


@router.post("/notify", response_model=FeishuCardSendResponse)
async def send_feishu_card_notification(
    request: FeishuCardSendRequest,
    db: AsyncSession = Depends(get_db),
):
    """Send Feishu interactive card notification to a user.

    Matches the user by username or full_name, then sends the card to their feishu_open_id.
    Records the notification in the database.
    """
    user = await _get_user_by_identifier(db, request.user)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.feishu_open_id:
        raise HTTPException(
            status_code=400,
            detail=f"User {user.username} does not have a feishu_open_id"
        )

    record_create = NotificationRecordCreate(
        user=request.user,
        matched_user=user.username,
        feishu_open_id=user.feishu_open_id,
        card_content=request.card_content,
        success=False,
        error=None,
    )
    notification_record_db = await notification_record.create(db, obj_in=record_create)

    try:
        feishu_service = get_feishu_service()
        result = feishu_service.send_message_to_user(
            user_id=user.feishu_open_id,
            msg_type="interactive",
            content=request.card_content,
        )

        if result.get("message_id"):
            await notification_record.update(
                db,
                record_id=notification_record_db.id,
                obj_in=NotificationRecordUpdate(
                    message_id=result["message_id"],
                    success=True,
                    error=result.get("msg"),
                ),
            )
            return FeishuCardSendResponse(
                success=True,
                message_id=result["message_id"],
                matched_user=user.username,
            )
        else:
            await notification_record.update(
                db,
                record_id=notification_record_db.id,
                obj_in=NotificationRecordUpdate(
                    success=False,
                    error=result.get("msg", "Unknown error"),
                ),
            )
            return FeishuCardSendResponse(
                success=False,
                matched_user=user.username,
                error=result.get("msg", "Unknown error"),
            )
    except RuntimeError as e:
        logger.error(f"[Feishu] Failed to send card notification: {e}")
        await notification_record.update(
            db,
            record_id=notification_record_db.id,
            obj_in=NotificationRecordUpdate(success=False, error=str(e)),
        )
        return FeishuCardSendResponse(
            success=False,
            matched_user=user.username,
            error=str(e),
        )

    except Exception as e:
        logger.error(f"[Feishu] Unexpected error sending card notification: {e}")
        await notification_record.update(
            db,
            record_id=notification_record_db.id,
            obj_in=NotificationRecordUpdate(success=False, error=str(e)),
        )
        return FeishuCardSendResponse(
            success=False,
            matched_user=user.username,
            error=str(e),
        )
