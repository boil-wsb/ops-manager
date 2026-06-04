"""
资产同步定时任务

从 Prometheus 自动同步资产数据
"""

from typing import Any

from app.config import settings
from app.core.logging import get_logger
from app.core.tz import now_shanghai
from app.db.session import db_operation_with_retry
from app.services.prometheus.asset_sync_optimized import OptimizedAssetSyncService

logger = get_logger(__name__)


async def _sync_all_assets_op(db) -> dict[str, Any]:
    service = OptimizedAssetSyncService(db)
    return await service.sync_all_assets()


async def _sync_single_asset_op(db, instance: str) -> dict[str, Any]:
    service = OptimizedAssetSyncService(db)
    return await service.sync_single_asset(instance)


async def sync_assets_from_prometheus_task() -> dict[str, Any]:
    """从 Prometheus 同步资产的任务

    每 30 分钟执行一次，自动发现和同步所有监控节点
    """
    if not getattr(settings, "PROMETHEUS_SYNC_ENABLED", True):
        logger.info("资产同步已禁用", extra={"action": "asset.sync"})
        return {"status": "skipped", "reason": "sync_disabled"}

    logger.debug("开始定时资产同步", extra={"action": "asset.sync"})
    start_time = now_shanghai()

    result = await db_operation_with_retry(_sync_all_assets_op, max_retries=3, retry_delay=2.0)

    end_time = now_shanghai()
    duration = (end_time - start_time).total_seconds()

    task_result = {
        "status": "success",
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "duration_seconds": duration,
        "total": result.get("total", 0),
        "created": result.get("created", 0),
        "updated": result.get("updated", 0),
        "failed": result.get("failed", 0),
        "errors": result.get("errors", []),
    }

    logger.info(
        "资产同步完成",
        extra={
            "action": "asset.sync",
            "total": task_result["total"],
            "created_count": task_result["created"],
            "updated_count": task_result["updated"],
            "failed_count": task_result["failed"],
        },
    )

    return task_result


async def sync_single_asset_task(instance: str) -> dict[str, Any]:
    """同步单个资产的任务

    Args:
        instance: Prometheus 实例标识 (IP:Port)
    """
    logger.debug("开始单资产同步", extra={"action": "asset.sync", "instance": instance})

    result = await db_operation_with_retry(
        lambda db: _sync_single_asset_op(db, instance), max_retries=3, retry_delay=2.0
    )

    if result["success"]:
        logger.info("资产同步成功", extra={"action": "asset.sync", "instance": instance})
        return {
            "status": "success",
            "instance": instance,
            "action": result.get("action"),
            "asset_id": result["asset"].asset_id if result["asset"] else None,
        }
    else:
        error_msg = result.get("error", "Unknown error")
        logger.error(
            f"资产同步失败: {error_msg}", extra={"action": "asset.sync", "instance": instance}
        )
        return {
            "status": "failed",
            "instance": instance,
            "error": error_msg,
        }


def get_sync_interval() -> float:
    """获取同步间隔（秒）

    从配置中读取，默认 30 分钟
    """
    interval_minutes = getattr(settings, "PROMETHEUS_SYNC_INTERVAL", 30)
    return float(interval_minutes * 60)
