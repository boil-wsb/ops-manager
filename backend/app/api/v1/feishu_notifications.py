"""
Feishu notification API endpoints.
"""

import asyncio
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.logging import get_logger
from app.crud.crud_notification_record import notification_record
from app.crud.crud_user import crud_user
from app.models.notification_record import NotificationRecord
from app.models.user import User
from app.schemas.notification_record import (
    NotificationRecordCreate,
    NotificationRecordUpdate,
)

logger = get_logger(__name__)


def get_feishu_service():
    from app.integrations.feishu.service import get_feishu_service as _get

    return _get()


router = APIRouter(prefix="/feishu", tags=["飞书通知"])


class FeishuCardSendRequest(BaseModel):
    card_content: dict[str, Any] = Field(..., description="飞书卡片 JSON 内容")
    user: str | None = Field(None, description="要匹配的用户名或 full_name（发送给个人）")
    chat_id: str | None = Field(None, description="飞书群聊 ID（发送到群聊）")
    callback_id: str | None = Field(None, description="业务回调标识，用于后续卡片更新")
    open_message_id: str | None = Field(
        None, description="自定义消息标识，用于后续按此标识更新卡片"
    )
    callback_url: str | None = Field(
        None, description="回调转发地址，卡片按钮点击时 POST 回调数据到该地址"
    )

    @model_validator(mode="after")
    def validate_target(self):
        if not self.user and not self.chat_id:
            raise ValueError("user 和 chat_id 必须提供其中一个")
        if self.user and self.chat_id:
            raise ValueError("user 和 chat_id 不能同时提供")
        if self.callback_url and not self.open_message_id:
            raise ValueError("提供 callback_url 时必须同时提供 open_message_id")
        if self.callback_url and not self.callback_url.startswith(("http://", "https://")):
            raise ValueError("callback_url 仅支持 http:// 或 https:// 协议")
        return self


class FeishuCardSendResponse(BaseModel):
    success: bool
    message_id: str | None = None
    matched_user: str | None = None
    chat_id: str | None = None
    callback_id: str | None = None
    open_message_id: str | None = None
    callback_url: str | None = None
    error: str | None = None


class FeishuCardUpdateRequest(BaseModel):
    card_content: dict[str, Any] | None = Field(
        None, description="更新后的飞书卡片 JSON 内容，为空时使用数据库中保存的内容"
    )
    callback_id: str | None = Field(
        None, description="业务回调标识，用于验证卡片归属（按 message_id 更新时必填）"
    )


class FeishuCardUpdateTargetResult(BaseModel):
    """单个目标的卡片更新结果（1:N 批量更新时使用）."""

    record_id: int
    message_id: str
    chat_id: str | None = None
    matched_user: str | None = None
    success: bool
    error: str | None = None


class FeishuCardUpdateResponse(BaseModel):
    success: bool
    message_id: str | None = None
    error: str | None = None
    # 1:N 场景: 按 open_message_id 批量更新时，每个目标的独立结果
    details: list[FeishuCardUpdateTargetResult] | None = None
    # 批量更新时的总数与成功数
    total: int | None = None
    succeeded: int | None = None


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

    result = await db.execute(select(User).where(and_(User.feishu_open_id == identifier)).limit(1))
    return result.scalar_one_or_none()


@router.post("/notify", response_model=FeishuCardSendResponse)
async def send_feishu_card_notification(
    request: FeishuCardSendRequest,
    db: AsyncSession = Depends(get_db),
):
    logger.info(
        f"Received request: user={request.user}, chat_id={request.chat_id}",
        extra={"action": "feishu.notify", "user": request.user, "chat_id": request.chat_id},
    )
    """Send Feishu interactive card notification to a user or chat.

    - If `chat_id` is provided, sends directly to the group chat.
    - If `user` is provided, matches the user and sends to their feishu_open_id.
    - `open_message_id` is an optional custom identifier for later card updates.
    Records the notification in the database.

    幂等性: 若 `open_message_id` + 目标（chat_id 或 user）已有 success=True 的记录，
    直接返回已有记录，避免调用方超时回退重发导致重复发送飞书卡片。
    注意: 同一 open_message_id 发送到多个群/用户是合法的 1:N 通知场景，
    幂等性检查必须加上目标维度，避免误杀多群通知。
    """
    # 幂等性检查: open_message_id + 目标 已有成功记录时直接返回，不重复发送
    # 根因: devops-webhook 超时回退重发会导致同一 (open_message_id, 目标) 的 2 次 POST 请求，
    # 两次都会发送飞书卡片到同一目标，造成重复通知。
    # 关键: 必须加上 chat_id/user 维度，否则 pipeline_5010 这种一次通知多群的场景会被误杀。
    if request.open_message_id:
        # 目标标识: chat_id 优先，否则用 user（user 字段在 NotificationRecord 里可能是 "chat:xxx" 或用户名）
        target_user = f"chat:{request.chat_id}" if request.chat_id else request.user
        idempotency_result = await db.execute(
            select(NotificationRecord)
            .where(
                NotificationRecord.open_message_id == request.open_message_id,
                NotificationRecord.user == target_user,
                NotificationRecord.success.is_(True),
            )
            .order_by(NotificationRecord.id.desc())
            .limit(1)
        )
        existing_record = idempotency_result.scalars().first()
        if existing_record:
            logger.info(
                f"幂等性检查命中: open_message_id={request.open_message_id} "
                f"target={target_user} 已有成功记录 id={existing_record.id}, 跳过重复发送",
                extra={
                    "action": "feishu.notify",
                    "open_message_id": request.open_message_id,
                    "target": target_user,
                    "existing_id": existing_record.id,
                },
            )
            return FeishuCardSendResponse(
                success=True,
                message_id=existing_record.message_id,
                matched_user=existing_record.matched_user,
                chat_id=existing_record.chat_id,
                callback_id=existing_record.callback_id,
                open_message_id=existing_record.open_message_id,
                callback_url=existing_record.callback_url,
            )

    if request.chat_id:
        record_create = NotificationRecordCreate(
            user=f"chat:{request.chat_id}",
            matched_user=None,
            feishu_open_id=None,
            chat_id=request.chat_id,
            receive_type="chat_id",
            callback_id=request.callback_id,
            open_message_id=request.open_message_id,
            callback_url=request.callback_url,
            card_content=request.card_content,
            success=False,
            error=None,
        )
        notification_record_db = await notification_record.create(db, obj_in=record_create)

        try:
            feishu_service = get_feishu_service()
            # 飞书 SDK 是同步阻塞调用，使用 asyncio.to_thread 避免阻塞事件循环
            # （历史教训：直调导致 devops-webhook 40s 超时回退重发，消息重复）
            result = await asyncio.to_thread(
                feishu_service.send_message_to_user,
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
                        open_message_id=request.open_message_id or result["message_id"],
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
                    callback_url=request.callback_url,
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
                    callback_url=request.callback_url,
                    error=result.get("msg", "Unknown error"),
                )
        except RuntimeError as e:
            logger.error(
                f"Failed to send card to chat: {e}",
                extra={"action": "feishu.notify", "chat_id": request.chat_id, "error": str(e)},
            )
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
                callback_url=request.callback_url,
                error=str(e),
            )

        except Exception as e:
            logger.error(
                f"Unexpected error sending card to chat: {e}",
                extra={"action": "feishu.notify", "chat_id": request.chat_id, "error": str(e)},
            )
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
                callback_url=request.callback_url,
                error=str(e),
            )

    user = await _get_user_by_identifier(db, request.user)

    if not user:
        logger.warning(
            f"User not found: {request.user}",
            extra={"action": "feishu.notify", "user": request.user},
        )
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
        callback_url=request.callback_url,
        card_content=request.card_content,
        success=False,
        error=None,
    )
    notification_record_db = await notification_record.create(db, obj_in=record_create)

    try:
        feishu_service = get_feishu_service()
        # 飞书 SDK 是同步阻塞调用，使用 asyncio.to_thread 避免阻塞事件循环
        result = await asyncio.to_thread(
            feishu_service.send_message_to_user,
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
                    open_message_id=request.open_message_id or result["message_id"],
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
                callback_url=request.callback_url,
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
                callback_url=request.callback_url,
                error=result.get("msg", "Unknown error"),
            )
    except RuntimeError as e:
        logger.error(
            f"Failed to send card notification: {e}",
            extra={"action": "feishu.notify", "user": user.username, "error": str(e)},
        )
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
            callback_url=request.callback_url,
            error=str(e),
        )

    except Exception as e:
        logger.error(
            f"Unexpected error sending card notification: {e}",
            extra={"action": "feishu.notify", "user": user.username, "error": str(e)},
        )
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
            callback_url=request.callback_url,
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
    try:
        result = await db.execute(
            select(NotificationRecord)
            .where(NotificationRecord.message_id == message_id)
            .order_by(NotificationRecord.id.desc())
            .limit(1)
        )
        record = result.scalars().first()
    except Exception as e:
        logger.error(
            f"DB query failed for message_id={message_id}: {e}",
            extra={"action": "feishu.notify", "message_id": message_id, "error": str(e)},
        )
        raise HTTPException(status_code=500, detail="Database query failed") from e

    if not record:
        raise HTTPException(status_code=404, detail="Notification record not found")

    if request.callback_id and record.callback_id and record.callback_id != request.callback_id:
        raise HTTPException(status_code=403, detail="callback_id does not match")

    card_content = request.card_content or record.card_content
    if not card_content:
        raise HTTPException(
            status_code=400, detail="No card_content provided and no saved content found"
        )

    try:
        feishu_service = get_feishu_service()
        # 飞书 SDK 是同步阻塞调用，使用 asyncio.to_thread 避免阻塞事件循环
        update_result = await asyncio.to_thread(
            feishu_service.update_card_message,
            open_message_id=message_id,
            card_content=card_content,
        )

        if update_result.get("success"):
            await notification_record.update(
                db,
                record_id=record.id,
                obj_in=NotificationRecordUpdate(
                    card_content=card_content,
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
        logger.error(
            f"Failed to update card: {e}",
            extra={"action": "feishu.notify", "message_id": message_id, "error": str(e)},
        )
        await notification_record.update(
            db,
            record_id=record.id,
            obj_in=NotificationRecordUpdate(success=False, error=str(e)),
        )
        return FeishuCardUpdateResponse(success=False, message_id=message_id, error=str(e))

    except Exception as e:
        logger.error(
            f"Unexpected error updating card: {e}",
            extra={"action": "feishu.notify", "message_id": message_id, "error": str(e)},
        )
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
    """Update Feishu interactive cards by open_message_id (支持 1:N 批量更新).

    Looks up ALL notification records matching open_message_id (success=True),
    then updates each card independently via Feishu API. Each target's update
    is isolated — one failure does not affect others.

    1:N 场景: 同一 open_message_id 可能已发送到多个群/用户（如 pipeline_5010
    发送到 2 个群），每张卡片有独立的 message_id，必须分别更新。

    Returns:
        - success=True 仅当所有目标都更新成功
        - details 字段包含每个目标的独立结果
    """
    try:
        result = await db.execute(
            select(NotificationRecord)
            .where(
                NotificationRecord.open_message_id == open_message_id,
                NotificationRecord.success.is_(True),
                NotificationRecord.message_id.isnot(None),
            )
            .order_by(NotificationRecord.id.asc())
        )
        records = result.scalars().all()
    except Exception as e:
        logger.error(
            f"DB query failed for open_message_id={open_message_id}: {e}",
            extra={"action": "feishu.notify", "open_message_id": open_message_id, "error": str(e)},
        )
        raise HTTPException(status_code=500, detail="Database query failed") from e

    if not records:
        raise HTTPException(
            status_code=404,
            detail="No successful notification records found by open_message_id",
        )

    # 校验 callback_id（所有记录的 callback_id 必须一致）
    if request.callback_id:
        for r in records:
            if r.callback_id and r.callback_id != request.callback_id:
                raise HTTPException(status_code=403, detail="callback_id does not match")

    feishu_service = get_feishu_service()
    details: list[FeishuCardUpdateTargetResult] = []
    succeeded = 0
    first_message_id: str | None = None
    first_error: str | None = None

    for record in records:
        if not record.message_id:
            details.append(
                FeishuCardUpdateTargetResult(
                    record_id=record.id,
                    message_id="",
                    chat_id=record.chat_id,
                    matched_user=record.matched_user,
                    success=False,
                    error="No Feishu message_id associated",
                )
            )
            continue

        if first_message_id is None:
            first_message_id = record.message_id

        # 卡片内容: 请求传入优先，否则用记录保存的
        card_content = request.card_content or record.card_content
        if not card_content:
            details.append(
                FeishuCardUpdateTargetResult(
                    record_id=record.id,
                    message_id=record.message_id,
                    chat_id=record.chat_id,
                    matched_user=record.matched_user,
                    success=False,
                    error="No card_content available",
                )
            )
            continue

        try:
            # 飞书 SDK 是同步阻塞调用，使用 asyncio.to_thread 避免阻塞事件循环
            update_result = await asyncio.to_thread(
                feishu_service.update_card_message,
                open_message_id=record.message_id,
                card_content=card_content,
            )

            if update_result.get("success"):
                await notification_record.update(
                    db,
                    record_id=record.id,
                    obj_in=NotificationRecordUpdate(
                        card_content=card_content,
                        success=True,
                    ),
                )
                succeeded += 1
                details.append(
                    FeishuCardUpdateTargetResult(
                        record_id=record.id,
                        message_id=record.message_id,
                        chat_id=record.chat_id,
                        matched_user=record.matched_user,
                        success=True,
                    )
                )
            else:
                err = update_result.get("error", "Unknown error")
                if first_error is None:
                    first_error = err
                await notification_record.update(
                    db,
                    record_id=record.id,
                    obj_in=NotificationRecordUpdate(success=False, error=err),
                )
                details.append(
                    FeishuCardUpdateTargetResult(
                        record_id=record.id,
                        message_id=record.message_id,
                        chat_id=record.chat_id,
                        matched_user=record.matched_user,
                        success=False,
                        error=err,
                    )
                )
        except Exception as e:
            logger.error(
                f"Failed to update card for record id={record.id} "
                f"(open_message_id={open_message_id}): {e}",
                extra={
                    "action": "feishu.notify",
                    "open_message_id": open_message_id,
                    "record_id": record.id,
                    "error": str(e),
                },
            )
            if first_error is None:
                first_error = str(e)
            await notification_record.update(
                db,
                record_id=record.id,
                obj_in=NotificationRecordUpdate(success=False, error=str(e)),
            )
            details.append(
                FeishuCardUpdateTargetResult(
                    record_id=record.id,
                    message_id=record.message_id,
                    chat_id=record.chat_id,
                    matched_user=record.matched_user,
                    success=False,
                    error=str(e),
                )
            )

    all_success = succeeded == len(records)
    logger.info(
        f"批量卡片更新完成 open_message_id={open_message_id}: "
        f"total={len(records)} succeeded={succeeded}",
        extra={
            "action": "feishu.notify",
            "open_message_id": open_message_id,
            "total": len(records),
            "succeeded": succeeded,
        },
    )
    return FeishuCardUpdateResponse(
        success=all_success,
        message_id=first_message_id,
        error=None if all_success else (first_error or "Partial failure"),
        details=details,
        total=len(records),
        succeeded=succeeded,
    )
