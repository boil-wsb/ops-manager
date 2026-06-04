"""
Feishu user sync tasks.
"""

from typing import Any

from app.core.logging import get_logger
from app.db.session import db_operation_with_retry

logger = get_logger(__name__)


async def _sync_feishu_users_db(db) -> dict[str, Any]:
    from app.crud.crud_user import crud_user
    from app.integrations.feishu.sync_service import sync_users

    result = await sync_users(db, crud_user)
    logger.info("飞书同步完成", extra={"action": "feishu.sync", "result": result})
    return result


async def sync_feishu_users_task() -> dict[str, Any]:
    """Sync Feishu users to local database.

    This task runs daily at 02:00 AM via Celery Beat.
    It performs incremental sync:
    - Creates new users from Feishu
    - Updates existing users if info changed
    - Deletes users no longer in Feishu scope
    """
    logger.info("开始飞书用户同步", extra={"action": "feishu.sync"})

    try:
        return await db_operation_with_retry(_sync_feishu_users_db, max_retries=3, retry_delay=2.0)
    except Exception as exc:
        logger.error(f"飞书同步失败: {exc}", extra={"action": "feishu.sync"})
        raise
