from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.logging import get_logger
from app.crud.crud_feishu_interaction import feishu_interaction
from app.models.user import User
from app.schemas.feishu_interaction import (
    FeishuInteractionListResponse,
    FeishuInteractionResponse,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/feishu", tags=["飞书交互记录"])


@router.get("/interactions", response_model=FeishuInteractionListResponse)
async def list_feishu_interactions(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    direction: str | None = Query(None, description="inbound 或 outbound"),
    interaction_type: str | None = Query(None, description="交互类型"),
    user_id: int | None = Query(None, description="用户 ID"),
    feishu_open_id: str | None = Query(None, description="飞书 Open ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    total, items = await feishu_interaction.get_multi(
        db,
        skip=skip,
        limit=limit,
        direction=direction,
        interaction_type=interaction_type,
        user_id=user_id,
        feishu_open_id=feishu_open_id,
    )
    return FeishuInteractionListResponse(total=total, items=items)


@router.get("/interactions/{interaction_id}", response_model=FeishuInteractionResponse)
async def get_feishu_interaction(
    interaction_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await feishu_interaction.get(db, interaction_id)
    if not result:
        raise HTTPException(status_code=404, detail="Interaction not found")
    return result


@router.get("/interactions-by-user/{user_id}", response_model=FeishuInteractionListResponse)
async def list_feishu_interactions_by_user(
    user_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    direction: str | None = Query(None),
    interaction_type: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    total, items = await feishu_interaction.get_multi(
        db,
        skip=skip,
        limit=limit,
        direction=direction,
        interaction_type=interaction_type,
        user_id=user_id,
    )
    return FeishuInteractionListResponse(total=total, items=items)
