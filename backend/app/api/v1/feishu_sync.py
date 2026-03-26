"""
Feishu user sync API endpoints.
"""
from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.crud.crud_user import crud_user

router = APIRouter(prefix="/feishu", tags=["feishu"])


async def _sync():
    """Internal sync function."""
    from app.db.session import get_async_session_local
    from app.integrations.feishu.sync_service import sync_users

    async with await get_async_session_local() as db:
        result = await sync_users(db, crud_user)
        return result


@router.post("/sync")
async def sync_feishu_users(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger Feishu user sync.

    This endpoint triggers an immediate sync of Feishu users to the local database.
    The sync runs in the background and returns immediately.
    """
    background_tasks.add_task(_sync)

    return {
        "message": "Feishu user sync started in background",
        "status": "pending",
    }


@router.post("/sync-sync")
async def sync_feishu_users_sync(
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger Feishu user sync (synchronous).

    This endpoint triggers an immediate sync and waits for the result.
    """
    from app.integrations.feishu.sync_service import sync_users
    result = await sync_users(db, crud_user)

    return {
        "message": "Feishu user sync completed",
        "result": result,
    }
