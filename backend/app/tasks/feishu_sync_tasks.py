"""
Feishu user sync tasks for Celery.
"""
import asyncio
from typing import Any

from celery import shared_task

from app.core.logging import get_logger
from app.tasks.utils import get_celery_async_session

logger = get_logger(__name__)


@shared_task(bind=True, max_retries=3)
def sync_feishu_users_task(self) -> dict[str, Any]:
    """Sync Feishu users to local database.

    This task runs daily at 02:00 AM via Celery Beat.
    It performs incremental sync:
    - Creates new users from Feishu
    - Updates existing users if info changed
    - Deletes users no longer in Feishu scope
    """
    from app.crud.crud_user import crud_user
    from app.integrations.feishu.sync_service import sync_users

    logger.info("Starting Feishu user sync task")

    async def _sync():
        session_local = get_celery_async_session()
        async with session_local() as db:
            result = await sync_users(db, crud_user)
            return result

    try:
        result = asyncio.run(_sync())
        logger.info(f"Feishu sync task completed: {result}")
        return result
    except Exception as exc:
        logger.error(f"Feishu sync task failed: {exc}")
        countdown = 300 * (5**self.request.retries)
        raise self.retry(exc=exc, countdown=countdown) from exc
