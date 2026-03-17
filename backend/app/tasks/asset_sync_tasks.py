"""
资产同步定时任务

从 Prometheus 自动同步资产数据
"""
import logging
from datetime import datetime
from typing import Dict, Any

from celery import shared_task
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.services.prometheus.asset_sync import AssetSyncService, sync_assets_from_prometheus
from app.config import settings

logger = logging.getLogger(__name__)


@shared_task(
    name="tasks.sync_assets_from_prometheus",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
async def sync_assets_from_prometheus_task(self) -> Dict[str, Any]:
    """
    从 Prometheus 同步资产的 Celery 任务

    每 30 分钟执行一次，自动发现和同步所有监控节点
    """
    # 检查是否启用同步
    if not getattr(settings, 'PROMETHEUS_SYNC_ENABLED', True):
        logger.info("Asset sync from Prometheus is disabled")
        return {"status": "skipped", "reason": "sync_disabled"}

    logger.info("Starting scheduled asset sync from Prometheus")
    start_time = datetime.utcnow()

    try:
        # 创建数据库会话
        async with AsyncSessionLocal() as db:
            try:
                # 执行同步
                result = await sync_assets_from_prometheus(db)

                end_time = datetime.utcnow()
                duration = (end_time - start_time).total_seconds()

                # 构建任务结果
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
                    f"Asset sync completed in {duration:.2f}s: "
                    f"total={task_result['total']}, "
                    f"created={task_result['created']}, "
                    f"updated={task_result['updated']}, "
                    f"failed={task_result['failed']}"
                )

                return task_result

            except Exception as e:
                await db.rollback()
                raise e
            finally:
                await db.close()

    except Exception as exc:
        logger.error(f"Asset sync task failed: {exc}")

        # 重试逻辑
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying asset sync task (attempt {self.request.retries + 1}/{self.max_retries})")
            raise self.retry(exc=exc)

        # 所有重试都失败
        return {
            "status": "failed",
            "start_time": start_time.isoformat(),
            "end_time": datetime.utcnow().isoformat(),
            "error": str(exc),
            "retry_exhausted": True,
        }


@shared_task(
    name="tasks.sync_single_asset",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
)
async def sync_single_asset_task(self, instance: str) -> Dict[str, Any]:
    """
    同步单个资产的 Celery 任务

    Args:
        instance: Prometheus 实例标识 (IP:Port)
    """
    logger.info(f"Starting single asset sync for instance: {instance}")

    try:
        async with AsyncSessionLocal() as db:
            try:
                service = AssetSyncService(db)
                result = await service.sync_single_asset(instance)

                if result["success"]:
                    logger.info(f"Successfully synced asset: {instance}")
                    return {
                        "status": "success",
                        "instance": instance,
                        "action": result.get("action"),
                        "asset_id": result["asset"].asset_id if result["asset"] else None,
                    }
                else:
                    error_msg = result.get("error", "Unknown error")
                    logger.error(f"Failed to sync asset {instance}: {error_msg}")
                    return {
                        "status": "failed",
                        "instance": instance,
                        "error": error_msg,
                    }

            except Exception as e:
                await db.rollback()
                raise e
            finally:
                await db.close()

    except Exception as exc:
        logger.error(f"Single asset sync task failed for {instance}: {exc}")

        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)

        return {
            "status": "failed",
            "instance": instance,
            "error": str(exc),
            "retry_exhausted": True,
        }


def get_sync_interval() -> float:
    """
    获取同步间隔（秒）

    从配置中读取，默认 30 分钟
    """
    interval_minutes = getattr(settings, 'PROMETHEUS_SYNC_INTERVAL', 30)
    return float(interval_minutes * 60)  # 转换为秒
