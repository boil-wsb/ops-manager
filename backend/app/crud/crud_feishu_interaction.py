import json
from datetime import datetime
from typing import Any

from sqlalchemy import create_engine, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.logging import get_logger
from app.core.tz import now_shanghai
from app.crud.base import CRUDBase
from app.models.feishu_interaction import FeishuInteraction
from app.schemas.feishu_interaction import FeishuInteractionCreate

logger = get_logger(__name__)


class CRUDFeishuInteraction(CRUDBase):
    def __init__(self):
        super().__init__(FeishuInteraction)

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 10,
        direction: str | None = None,
        interaction_type: str | None = None,
        user_id: int | None = None,
        feishu_open_id: str | None = None,
    ) -> tuple[int, list[FeishuInteraction]]:
        query = select(FeishuInteraction)

        if direction:
            query = query.where(FeishuInteraction.direction == direction)
        if interaction_type:
            query = query.where(FeishuInteraction.interaction_type == interaction_type)
        if user_id:
            query = query.where(FeishuInteraction.user_id == user_id)
        if feishu_open_id:
            query = query.where(FeishuInteraction.feishu_open_id == feishu_open_id)

        query = query.order_by(FeishuInteraction.created_at.desc())

        total_query = select(func.count()).select_from(query.subquery())
        total = (await db.execute(total_query)).scalar() or 0

        query = query.offset(skip).limit(limit)
        items = (await db.execute(query)).scalars().all()

        return total, list(items)

    async def create(
        self,
        db: AsyncSession,
        *,
        obj_in: FeishuInteractionCreate,
    ) -> FeishuInteraction:
        db_obj = FeishuInteraction(
            direction=obj_in.direction,
            interaction_type=obj_in.interaction_type,
            user_id=obj_in.user_id,
            feishu_open_id=obj_in.feishu_open_id,
            message_id=obj_in.message_id,
            chat_id=obj_in.chat_id,
            content=obj_in.content,
            msg_type=obj_in.msg_type,
            action_type=obj_in.action_type,
            related_type=obj_in.related_type,
            related_id=obj_in.related_id,
            status=obj_in.status,
            error=obj_in.error,
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj


def _get_sync_engine():
    sync_db_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    return create_engine(sync_db_url, pool_pre_ping=True)


def _resolve_user_id_by_open_id(open_id: str | None) -> int | None:
    if not open_id:
        return None
    try:
        engine = _get_sync_engine()
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT id FROM users WHERE feishu_open_id = :open_id"),
                {"open_id": open_id},
            )
            row = result.fetchone()
        engine.dispose()
        return row[0] if row else None
    except Exception as e:
        logger.error(f"解析用户ID失败: {e}", extra={"action": "feishu.interaction", "open_id": open_id, "error": str(e)})
        return None


def record_interaction_sync(
    *,
    direction: str,
    interaction_type: str,
    feishu_open_id: str | None = None,
    message_id: str | None = None,
    chat_id: str | None = None,
    content: dict[str, Any] | None = None,
    msg_type: str | None = None,
    action_type: str | None = None,
    related_type: str | None = None,
    related_id: str | None = None,
    status: str = "success",
    error: str | None = None,
) -> None:
    try:
        user_id = _resolve_user_id_by_open_id(feishu_open_id)
        engine = _get_sync_engine()
        with engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO feishu_interactions
                    (direction, interaction_type, user_id, feishu_open_id, message_id,
                     chat_id, content, msg_type, action_type, related_type, related_id,
                     status, error, created_at, updated_at)
                    VALUES
                    (:direction, :interaction_type, :user_id, :feishu_open_id, :message_id,
                     :chat_id, :content, :msg_type, :action_type, :related_type, :related_id,
                     :status, :error, :created_at, :updated_at)
                """),
                {
                    "direction": direction,
                    "interaction_type": interaction_type,
                    "user_id": user_id,
                    "feishu_open_id": feishu_open_id,
                    "message_id": message_id,
                    "chat_id": chat_id,
                    "content": json.dumps(content, ensure_ascii=False) if content else None,
                    "msg_type": msg_type,
                    "action_type": action_type,
                    "related_type": related_type,
                    "related_id": related_id,
                    "status": status,
                    "error": error,
                    "created_at": now_shanghai(),
                    "updated_at": now_shanghai(),
                },
            )
            conn.commit()
        engine.dispose()
    except Exception as e:
        logger.error(f"记录飞书交互失败: {e}", extra={"action": "feishu.interaction", "error": str(e)})


feishu_interaction = CRUDFeishuInteraction()
