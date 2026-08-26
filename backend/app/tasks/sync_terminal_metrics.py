"""
终端指标同步定时任务

从 Prometheus 同步终端指标数据
"""

import asyncio
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from app.core.logging import get_logger
from app.core.tz import now_shanghai
from app.db.session import db_operation_with_retry, ensure_pool_health, log_pool_status
from app.models.asset import Asset, AssetType
from app.services.prometheus.client import PrometheusClient

logger = get_logger(__name__)

# 每批处理的终端数量（减小批次降低单次事务时长）
BATCH_SIZE = 10
# 批次间延迟（秒），减少数据库压力
BATCH_DELAY = 1.0


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
    return asset.id


async def _write_terminal_batch(db, terminals: list[dict]) -> int:
    """将一批终端指标数据写入数据库。

    注意：此函数在 db_operation_with_retry 内调用，db 会话由其管理。
    循环内仅 flush，循环结束后统一 commit。
    """
    from app.crud import crud_terminal_metric

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
    return synced_count


async def sync_terminal_metrics_task() -> dict[str, Any]:
    """从 Prometheus 同步终端指标的异步任务

    每 10 分钟执行一次，同步终端性能指标到 terminal_metrics 表。

    关键优化：
    1. 先在 DB 会话外获取 Prometheus 数据（耗时操作）
    2. 写入前检查连接池健康状态
    3. 分批写入数据库，每批使用独立的 DB 会话和事务
    4. 批次间添加延迟，减少数据库压力，避免阻塞其他请求
    """
    start_time = now_shanghai()
    logger.info("开始定时终端指标同步", extra={"action": "terminal.metrics"})
    log_pool_status()

    # 第一步：在 DB 会话外获取 Prometheus 数据（耗时操作）
    prom_start = now_shanghai()
    client = PrometheusClient()
    terminals = await client.get_all_terminals_with_metrics()
    prom_duration = (now_shanghai() - prom_start).total_seconds()
    logger.info(
        f"Prometheus 数据获取完成: {len(terminals)} 个终端, 耗时 {prom_duration:.1f}s",
        extra={
            "action": "terminal.metrics",
            "terminals": len(terminals),
            "prom_duration": prom_duration,
        },
    )
    log_pool_status()

    if not terminals:
        return {
            "status": "success",
            "total_terminals": 0,
            "synced": 0,
            "duration_seconds": 0,
        }

    # 第二步：写入前检查连接池健康状态
    await ensure_pool_health()

    # 第三步：分批写入数据库
    total_synced = 0
    batch_errors = []

    for i in range(0, len(terminals), BATCH_SIZE):
        batch = terminals[i : i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        total_batches = (len(terminals) + BATCH_SIZE - 1) // BATCH_SIZE

        batch_start = now_shanghai()
        try:
            synced = await db_operation_with_retry(
                lambda db, b=batch: _write_terminal_batch(db, b),
                max_retries=3,
                retry_delay=2.0,
            )
            total_synced += synced
            batch_duration = (now_shanghai() - batch_start).total_seconds()
            logger.info(
                f"批次 {batch_num}/{total_batches} 写入完成: {synced} 条, 耗时 {batch_duration:.1f}s",
                extra={
                    "action": "terminal.metrics",
                    "batch": batch_num,
                    "duration": batch_duration,
                },
            )
        except Exception as e:
            batch_errors.append(f"Batch {batch_num}: {str(e)}")
            logger.error(
                f"批次 {batch_num}/{total_batches} 写入失败: {e}",
                extra={"action": "terminal.metrics", "batch": batch_num, "error": str(e)},
            )

        # 批次间延迟，给数据库喘息空间
        if i + BATCH_SIZE < len(terminals):
            await asyncio.sleep(BATCH_DELAY)

    end_time = now_shanghai()
    duration = (end_time - start_time).total_seconds()

    task_result = {
        "status": "success" if not batch_errors else "partial",
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "duration_seconds": duration,
        "total_terminals": len(terminals),
        "synced": total_synced,
        "errors": batch_errors if batch_errors else None,
    }

    logger.info(
        "终端指标同步完成",
        extra={
            "action": "terminal.metrics",
            "total": task_result["total_terminals"],
            "synced": task_result["synced"],
            "duration_seconds": duration,
            "errors": len(batch_errors),
        },
    )
    log_pool_status()

    return task_result


def get_sync_interval() -> float:
    """获取同步间隔（秒）

    默认 10 分钟
    """
    return 10 * 60
