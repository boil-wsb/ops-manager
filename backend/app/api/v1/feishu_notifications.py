"""
Feishu notification API endpoints.
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.crud.crud_notification_record import notification_record
from app.crud.crud_user import crud_user
from app.models.notification_record import NotificationRecord
from app.models.user import User
from app.schemas.notification_record import (
    NotificationRecordCreate,
    NotificationRecordUpdate,
)

logger = logging.getLogger(__name__)


def get_feishu_service():
    from app.integrations.feishu.service import get_feishu_service as _get

    return _get()


router = APIRouter(prefix="/feishu", tags=["飞书通知"])


class FeishuCardSendRequest(BaseModel):
    card_content: dict[str, Any] = Field(..., description="飞书卡片 JSON 内容")
    user: str | None = Field(None, description="要匹配的用户名或 full_name（发送给个人）")
    chat_id: str | None = Field(None, description="飞书群聊 ID（发送到群聊）")
    callback_id: str | None = Field(None, description="业务回调标识，用于后续卡片更新")
    open_message_id: str | None = Field(None, description="自定义消息标识，用于后续按此标识更新卡片")

    @model_validator(mode="after")
    def validate_target(self):
        if not self.user and not self.chat_id:
            raise ValueError("user 和 chat_id 必须提供其中一个")
        if self.user and self.chat_id:
            raise ValueError("user 和 chat_id 不能同时提供")
        return self


class FeishuCardSendResponse(BaseModel):
    success: bool
    message_id: str | None = None
    matched_user: str | None = None
    chat_id: str | None = None
    callback_id: str | None = None
    open_message_id: str | None = None
    error: str | None = None


class FeishuCardUpdateRequest(BaseModel):
    card_content: dict[str, Any] = Field(..., description="更新后的飞书卡片 JSON 内容")
    callback_id: str | None = Field(None, description="业务回调标识，用于验证卡片归属（按 message_id 更新时必填）")


class FeishuCardUpdateResponse(BaseModel):
    success: bool
    message_id: str | None = None
    error: str | None = None


async def _get_user_by_identifier(db: AsyncSession, identifier: str) -> User | None:
    user = await crud_user.get_by_username(db, username=identifier)
    if user:
        return user

    result = await db.execute(
        select(User)
        .where(and_(User.full_name == identifier, User.feishu_open_id.isnot(None)))
        .limit(1)
    )
    user = result.scalar_one_or_none()
    if user:
        return user

    result = await db.execute(
        select(User)
        .where(and_(User.feishu_open_id == identifier))
        .limit(1)
    )
    return result.scalar_one_or_none()


@router.post("/notify", response_model=FeishuCardSendResponse)
async def send_feishu_card_notification(
    request: FeishuCardSendRequest,
    db: AsyncSession = Depends(get_db),
):
    logger.info(f"[Feishu Notify] Received request: user={request.user}, chat_id={request.chat_id}")
    """Send Feishu interactive card notification to a user or chat.

    - If `chat_id` is provided, sends directly to the group chat.
    - If `user` is provided, matches the user and sends to their feishu_open_id.
    - `open_message_id` is an optional custom identifier for later card updates.
    Records the notification in the database.
    """
    if request.chat_id:
        record_create = NotificationRecordCreate(
            user=f"chat:{request.chat_id}",
            matched_user=None,
            feishu_open_id=None,
            chat_id=request.chat_id,
            receive_type="chat_id",
            callback_id=request.callback_id,
            open_message_id=request.open_message_id,
            card_content=request.card_content,
            success=False,
            error=None,
        )
        notification_record_db = await notification_record.create(db, obj_in=record_create)

        try:
            feishu_service = get_feishu_service()
            result = feishu_service.send_message_to_user(
                user_id=request.chat_id,
                msg_type="interactive",
                content=request.card_content,
                receive_id_type="chat_id",
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
                    chat_id=request.chat_id,
                    callback_id=request.callback_id,
                    open_message_id=request.open_message_id,
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
                    chat_id=request.chat_id,
                    callback_id=request.callback_id,
                    open_message_id=request.open_message_id,
                    error=result.get("msg", "Unknown error"),
                )
        except RuntimeError as e:
            logger.error(f"[Feishu] Failed to send card to chat: {e}")
            await notification_record.update(
                db,
                record_id=notification_record_db.id,
                obj_in=NotificationRecordUpdate(success=False, error=str(e)),
            )
            return FeishuCardSendResponse(
                success=False,
                chat_id=request.chat_id,
                callback_id=request.callback_id,
                open_message_id=request.open_message_id,
                error=str(e),
            )

        except Exception as e:
            logger.error(f"[Feishu] Unexpected error sending card to chat: {e}")
            await notification_record.update(
                db,
                record_id=notification_record_db.id,
                obj_in=NotificationRecordUpdate(success=False, error=str(e)),
            )
            return FeishuCardSendResponse(
                success=False,
                chat_id=request.chat_id,
                callback_id=request.callback_id,
                open_message_id=request.open_message_id,
                error=str(e),
            )

    user = await _get_user_by_identifier(db, request.user)

    if not user:
        logger.warning(f"[Feishu Notify] User not found: {request.user}")
        raise HTTPException(status_code=404, detail="User not found")

    if not user.feishu_open_id:
        raise HTTPException(
            status_code=400, detail=f"User {user.username} does not have a feishu_open_id"
        )

    record_create = NotificationRecordCreate(
        user=request.user,
        matched_user=user.username,
        feishu_open_id=user.feishu_open_id,
        chat_id=None,
        receive_type="open_id",
        callback_id=request.callback_id,
        open_message_id=request.open_message_id,
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
                callback_id=request.callback_id,
                open_message_id=request.open_message_id,
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
                callback_id=request.callback_id,
                open_message_id=request.open_message_id,
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
            callback_id=request.callback_id,
            open_message_id=request.open_message_id,
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
            callback_id=request.callback_id,
            open_message_id=request.open_message_id,
            error=str(e),
        )


@router.patch("/notify/{message_id}", response_model=FeishuCardUpdateResponse)
async def update_feishu_card(
    message_id: str,
    request: FeishuCardUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update a Feishu interactive card by message_id.

    Validates callback_id matches the original record before updating.
    """
    result = await db.execute(
        select(NotificationRecord).where(NotificationRecord.message_id == message_id)
    )
    record = result.scalar_one_or_none()

    if not record:
        raise HTTPException(status_code=404, detail="Notification record not found")

    if request.callback_id and record.callback_id != request.callback_id:
        raise HTTPException(status_code=403, detail="callback_id does not match")

    try:
        feishu_service = get_feishu_service()
        update_result = feishu_service.update_card_message(
            open_message_id=message_id,
            card_content=request.card_content,
        )

        if update_result.get("success"):
            await notification_record.update(
                db,
                record_id=record.id,
                obj_in=NotificationRecordUpdate(
                    card_content=request.card_content,
                    success=True,
                ),
            )
            return FeishuCardUpdateResponse(
                success=True,
                message_id=message_id,
            )
        else:
            await notification_record.update(
                db,
                record_id=record.id,
                obj_in=NotificationRecordUpdate(
                    success=False,
                    error=update_result.get("error", "Unknown error"),
                ),
            )
            return FeishuCardUpdateResponse(
                success=False,
                message_id=message_id,
                error=update_result.get("error", "Unknown error"),
            )
    except RuntimeError as e:
        logger.error(f"[Feishu] Failed to update card: {e}")
        await notification_record.update(
            db,
            record_id=record.id,
            obj_in=NotificationRecordUpdate(success=False, error=str(e)),
        )
        return FeishuCardUpdateResponse(success=False, message_id=message_id, error=str(e))

    except Exception as e:
        logger.error(f"[Feishu] Unexpected error updating card: {e}")
        await notification_record.update(
            db,
            record_id=record.id,
            obj_in=NotificationRecordUpdate(success=False, error=str(e)),
        )
        return FeishuCardUpdateResponse(success=False, message_id=message_id, error=str(e))


@router.patch("/notify-by-open-id/{open_message_id}", response_model=FeishuCardUpdateResponse)
async def update_feishu_card_by_open_message_id(
    open_message_id: str,
    request: FeishuCardUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update a Feishu interactive card by open_message_id.

    Looks up the notification record by open_message_id, then uses the stored
    Feishu message_id to update the card.
    """
    result = await db.execute(
        select(NotificationRecord).where(
            NotificationRecord.open_message_id == open_message_id
        )
    )
    record = result.scalar_one_or_none()

    if not record:
        raise HTTPException(status_code=404, detail="Notification record not found by open_message_id")

    if not record.message_id:
        raise HTTPException(status_code=400, detail="No Feishu message_id associated with this record")

    if request.callback_id and record.callback_id and record.callback_id != request.callback_id:
        raise HTTPException(status_code=403, detail="callback_id does not match")

    try:
        feishu_service = get_feishu_service()
        update_result = feishu_service.update_card_message(
            open_message_id=record.message_id,
            card_content=request.card_content,
        )

        if update_result.get("success"):
            await notification_record.update(
                db,
                record_id=record.id,
                obj_in=NotificationRecordUpdate(
                    card_content=request.card_content,
                    success=True,
                ),
            )
            return FeishuCardUpdateResponse(
                success=True,
                message_id=record.message_id,
            )
        else:
            await notification_record.update(
                db,
                record_id=record.id,
                obj_in=NotificationRecordUpdate(
                    success=False,
                    error=update_result.get("error", "Unknown error"),
                ),
            )
            return FeishuCardUpdateResponse(
                success=False,
                message_id=record.message_id,
                error=update_result.get("error", "Unknown error"),
            )
    except RuntimeError as e:
        logger.error(f"[Feishu] Failed to update card by open_message_id: {e}")
        await notification_record.update(
            db,
            record_id=record.id,
            obj_in=NotificationRecordUpdate(success=False, error=str(e)),
        )
        return FeishuCardUpdateResponse(success=False, message_id=record.message_id, error=str(e))

    except Exception as e:
        logger.error(f"[Feishu] Unexpected error updating card by open_message_id: {e}")
        await notification_record.update(
            db,
            record_id=record.id,
            obj_in=NotificationRecordUpdate(success=False, error=str(e)),
        )
        return FeishuCardUpdateResponse(success=False, message_id=record.message_id, error=str(e))
