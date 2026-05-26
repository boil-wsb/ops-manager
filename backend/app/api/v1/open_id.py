from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.logging import get_logger
from app.models.user import User
from app.schemas.open_id import OpenIdResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/open-id", tags=["Open ID 查询"])


@router.get("", response_model=OpenIdResponse)
async def get_open_id(
    name: str = Query(..., description="中文姓名（支持模糊匹配）"),
    db: AsyncSession = Depends(get_db),
):
    logger.info(f"Open ID query: name='{name}'", extra={"action": "feishu.openid", "query_name": name})
    result = await db.execute(
        select(User).where(
            and_(
                User.full_name.ilike(f"%{name}%"),
                User.feishu_open_id.isnot(None),
                User.is_active == True,
            )
        ).limit(20)
    )
    users = result.scalars().all()
    logger.info(f"Open ID query result: name='{name}', matched={len(users)}", extra={"action": "feishu.openid", "query_name": name, "matched": len(users)})
    return {"items": users}
