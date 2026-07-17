"""
Terminal Metric CRUD operations.
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.crud.base import CRUDBase
from app.models.terminal_metric import TerminalMetric

logger = get_logger(__name__)


class CRUDBerminalMetric(CRUDBase[TerminalMetric, Any, Any]):
    """Terminal Metric CRUD operations."""

    async def get_multi_by_owner(
        self,
        db: AsyncSession,
        *,
        owner_username: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[TerminalMetric]:
        """Get terminal metrics by owner username."""
        query = (
            select(TerminalMetric)
            .where(TerminalMetric.owner_username == owner_username)
            .order_by(TerminalMetric.hostname)
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_summary_by_owner(
        self,
        db: AsyncSession,
        *,
        owner_username: str,
    ) -> dict[str, Any]:
        """Get summary statistics for owner's terminals."""
        query = select(TerminalMetric).where(TerminalMetric.owner_username == owner_username)
        result = await db.execute(query)
        metrics = list(result.scalars().all())

        if not metrics:
            return {
                "total_count": 0,
                "online_count": 0,
                "offline_count": 0,
                "alert_count": 0,
                "avg_cpu_usage": 0.0,
                "avg_memory_usage": 0.0,
                "avg_disk_usage": 0.0,
            }

        total = len(metrics)
        online = sum(1 for m in metrics if m.current_status == "online")
        offline = sum(1 for m in metrics if m.current_status == "offline")
        alerts = sum(m.alert_count for m in metrics)

        cpu_values = [m.cpu_usage for m in metrics if m.cpu_usage is not None]
        memory_values = [m.memory_usage for m in metrics if m.memory_usage is not None]
        disk_values = [m.disk_usage for m in metrics if m.disk_usage is not None]

        return {
            "total_count": total,
            "online_count": online,
            "offline_count": offline,
            "alert_count": alerts,
            "avg_cpu_usage": round(sum(cpu_values) / len(cpu_values), 1) if cpu_values else 0.0,
            "avg_memory_usage": round(sum(memory_values) / len(memory_values), 1)
            if memory_values
            else 0.0,
            "avg_disk_usage": round(sum(disk_values) / len(disk_values), 1) if disk_values else 0.0,
        }

    async def upsert_metric(
        self,
        db: AsyncSession,
        *,
        asset_id: int,
        hostname: str,
        owner_username: str,
        ip_address: str | None = None,
        cpu_usage: float | None = None,
        memory_usage: float | None = None,
        memory_total_gb: float | None = None,
        disk_usage: float | None = None,
        disk_total_gb: float | None = None,
        network_in: float | None = None,
        network_out: float | None = None,
        uptime_hours: int | None = None,
        last_heartbeat: datetime | None = None,
        current_status: str = "unknown",
        alert_count: int = 0,
        alert_severity: str | None = None,
        monitor_name: str | None = None,
    ) -> TerminalMetric:
        """Insert or update a terminal metric.

        C-09 修复：改用 PostgreSQL INSERT ... ON CONFLICT (asset_id) DO UPDATE，
        原子性保证，彻底消除 SELECT-then-UPDATE 的 TOCTOU 竞态和并发累积重复行问题。
        依赖 terminal_metrics.asset_id 的 UNIQUE 约束（迁移 20260717_0004）。
        """
        now = datetime.now(UTC)

        values = {
            "asset_id": asset_id,
            "hostname": hostname,
            "owner_username": owner_username,
            "ip_address": ip_address,
            "cpu_usage": cpu_usage,
            "memory_usage": memory_usage,
            "memory_total_gb": memory_total_gb,
            "disk_usage": disk_usage,
            "disk_total_gb": disk_total_gb,
            "network_in": network_in,
            "network_out": network_out,
            "uptime_hours": uptime_hours,
            "last_heartbeat": last_heartbeat,
            "current_status": current_status,
            "alert_count": alert_count,
            "alert_severity": alert_severity,
            "monitor_name": monitor_name,
            "metrics_timestamp": now,
            "created_at": now,
            "updated_at": now,
        }

        update_set = {
            "owner_username": owner_username,
            "hostname": hostname,
            "ip_address": ip_address,
            "cpu_usage": cpu_usage,
            "memory_usage": memory_usage,
            "memory_total_gb": memory_total_gb,
            "disk_usage": disk_usage,
            "disk_total_gb": disk_total_gb,
            "network_in": network_in,
            "network_out": network_out,
            "uptime_hours": uptime_hours,
            "last_heartbeat": last_heartbeat,
            "current_status": current_status,
            "alert_count": alert_count,
            "alert_severity": alert_severity,
            "monitor_name": monitor_name,
            "metrics_timestamp": now,
            "updated_at": now,
        }

        stmt = pg_insert(TerminalMetric).values(**values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["asset_id"],
            set_=update_set,
        )
        await db.execute(stmt)
        await db.flush()

        # ON CONFLICT 后查询返回 ORM 对象（UNIQUE 约束保证仅 1 行）
        result = await db.execute(
            select(TerminalMetric).where(TerminalMetric.asset_id == asset_id)
        )
        return result.scalar_one()

    async def get_last_sync_time(
        self,
        db: AsyncSession,
        *,
        owner_username: str,
    ) -> datetime | None:
        """Get the last sync time for owner's terminals."""
        query = select(func.max(TerminalMetric.metrics_timestamp)).where(
            TerminalMetric.owner_username == owner_username
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()


crud_terminal_metric = CRUDBerminalMetric(TerminalMetric)
