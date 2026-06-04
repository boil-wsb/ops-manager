"""
终端指标同步定时任务

从 Prometheus 同步终端指标数据
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from app.core.logging import get_logger
from app.core.tz import now_shanghai
from app.db.session import db_operation_with_retry
from app.models.asset import Asset, AssetType
from app.services.prometheus.client import PrometheusClient

logger = get_logger(__name__)


async def get_or_create_asset(
    db,
    hostname: str,
    instance: str,
    customer: str,
) -> int:
    """Get or create an asset for the terminal."""
    result = await db.execute(select(Asset).where(Asset.hostname == hostname))
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


async def _sync_terminal_metrics_db(db) -> dict[str, Any]:
    from app.crud import crud_terminal_metric

    start_time = now_shanghai()

    client = PrometheusClient()

    terminals = await client.get_all_terminals_with_metrics()
    logger.debug(f"发现 {len(terminals)} 个终端", extra={"action": "terminal.metrics"})

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

        asset_id = await get_or_create_asset(db, hostname, instance, customer)

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

    end_time = now_shanghai()
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
        "终端指标同步完成",
        extra={
            "action": "terminal.metrics",
            "total": task_result["total_terminals"],
            "synced": task_result["synced"],
            "duration_seconds": duration,
        },
    )

    return task_result


async def sync_terminal_metrics_task() -> dict[str, Any]:
    """从 Prometheus 同步终端指标的异步任务

    每 5 分钟执行一次，同步终端性能指标到 terminal_metrics 表
    """
    logger.debug("开始定时终端指标同步", extra={"action": "terminal.metrics"})

    try:
        return await db_operation_with_retry(
            _sync_terminal_metrics_db, max_retries=3, retry_delay=2.0
        )
    except Exception:
        raise


def get_sync_interval() -> float:
    """获取同步间隔（秒）

    默认 5 分钟
    """
    return 5 * 60
