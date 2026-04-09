"""
终端指标同步定时任务

从 Prometheus 同步终端指标数据
"""
import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from celery import shared_task
from sqlalchemy import select

from app.models.asset import Asset, AssetType
from app.services.prometheus.client import PrometheusClient
from app.tasks.utils import get_celery_async_session

logger = logging.getLogger(__name__)


async def get_or_create_asset(
    db,
    hostname: str,
    instance: str,
    customer: str,
) -> int:
    """Get or create an asset for the terminal."""
    result = await db.execute(
        select(Asset).where(Asset.hostname == hostname)
    )
    asset = result.scalar_one_or_none()

    if asset:
        return asset.id

    asset = Asset(
        asset_id=f"TERMINAL-{hostname}",
        name=hostname,
        asset_type=AssetType.TERMINAL,
        hostname=hostname,
        ip_address=instance.split(":")[0] if instance else None,
        customer=customer,
        source="PROMETHEUS",
    )
    db.add(asset)
    await db.flush()
    await db.refresh(asset)
    return asset.id


@shared_task(
    name="tasks.sync_terminal_metrics",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def sync_terminal_metrics_task(self) -> dict[str, Any]:
    """从 Prometheus 同步终端指标的 Celery 任务

    每 5 分钟执行一次，同步终端性能指标到 terminal_metrics 表
    """
    logger.info("Starting scheduled terminal metrics sync from Prometheus")
    start_time = datetime.utcnow()

    async def _sync():
        session_local = get_celery_async_session()

        async with session_local() as db:
            try:
                from app.crud import crud_terminal_metric

                client = PrometheusClient()

                terminals = await client.get_all_terminals_with_metrics()
                logger.info(f"Found {len(terminals)} terminals from Prometheus")

                synced_count = 0
                for terminal in terminals:
                    hostname = terminal.get("hostname", "")
                    if not hostname:
                        continue

                    customer = terminal.get("customer", "")
                    instance = terminal.get("instance", "")

                    disk_usage = terminal.get("disk_usage", 0)
                    memory_usage = terminal.get("memory_usage", 0)
                    cpu_usage = terminal.get("cpu_usage", 0)
                    disk_total_bytes = terminal.get("disk_total", 0)
                    memory_total_bytes = terminal.get("memory_total", 0)
                    disk_total_gb = round(disk_total_bytes / (1024**3), 1) if disk_total_bytes else None
                    memory_total_gb = round(memory_total_bytes / (1024**3), 1) if memory_total_bytes else None

                    asset_id = await get_or_create_asset(
                        db, hostname, instance, customer
                    )

                    await crud_terminal_metric.upsert_metric(
                        db,
                        asset_id=asset_id,
                        hostname=hostname,
                        owner_username=customer,
                        ip_address=instance.split(":")[0] if instance else None,
                        cpu_usage=cpu_usage,
                        memory_usage=memory_usage,
                        memory_total_gb=memory_total_gb,
                        disk_usage=disk_usage,
                        disk_total_gb=disk_total_gb,
                        network_in=None,
                        network_out=None,
                        uptime_hours=None,
                        last_heartbeat=datetime.now(UTC),
                        current_status="online",
                        alert_count=0,
                        alert_severity=None,
                        monitor_name="pcinfo",
                    )
                    synced_count += 1

                await db.commit()

                end_time = datetime.utcnow()
                duration = (end_time - start_time).total_seconds()

                task_result = {
                    "status": "success",
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "duration_seconds": duration,
                    "total_terminals": len(terminals),
                    "synced": synced_count,
                }

                logger.info(
                    f"Terminal metrics sync completed in {duration:.2f}s: "
                    f"total={task_result['total_terminals']}, synced={task_result['synced']}"
                )

                return task_result

            except Exception as e:
                await db.rollback()
                raise e from e

    try:
        return asyncio.run(_sync())
    except Exception as exc:
        logger.error(f"Terminal metrics sync task failed: {exc}")

        if self.request.retries < self.max_retries:
            logger.info(
                f"Retrying terminal metrics sync task (attempt {self.request.retries + 1}/{self.max_retries})"
            )
            raise self.retry(exc=exc) from exc

        return {
            "status": "failed",
            "start_time": start_time.isoformat(),
            "end_time": datetime.utcnow().isoformat(),
            "error": str(exc),
            "retry_exhausted": True,
        }


def get_sync_interval() -> float:
    """获取同步间隔（秒）

    默认 5 分钟
    """
    return 5 * 60
