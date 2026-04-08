"""
Terminal Metric CRUD operations.
"""
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.terminal_metric import TerminalMetric


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
            "avg_memory_usage": round(sum(memory_values) / len(memory_values), 1) if memory_values else 0.0,
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
        disk_usage: float | None = None,
        network_in: float | None = None,
        network_out: float | None = None,
        uptime_hours: int | None = None,
        last_heartbeat: datetime | None = None,
        current_status: str = "unknown",
        alert_count: int = 0,
        alert_severity: str | None = None,
        monitor_name: str | None = None,
    ) -> TerminalMetric:
        """Insert or update a terminal metric."""
        query = select(TerminalMetric).where(TerminalMetric.asset_id == asset_id)
        result = await db.execute(query)
        metric = result.scalar_one_or_none()

        now = datetime.now(UTC)

        if metric:
            metric.owner_username = owner_username
            metric.hostname = hostname
            metric.ip_address = ip_address
            metric.cpu_usage = cpu_usage
            metric.memory_usage = memory_usage
            metric.disk_usage = disk_usage
            metric.network_in = network_in
            metric.network_out = network_out
            metric.uptime_hours = uptime_hours
            metric.last_heartbeat = last_heartbeat
            metric.current_status = current_status
            metric.alert_count = alert_count
            metric.alert_severity = alert_severity
            metric.monitor_name = monitor_name
            metric.metrics_timestamp = now
            metric.updated_at = now
        else:
            metric = TerminalMetric(
                asset_id=asset_id,
                hostname=hostname,
                owner_username=owner_username,
                ip_address=ip_address,
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                disk_usage=disk_usage,
                network_in=network_in,
                network_out=network_out,
                uptime_hours=uptime_hours,
                last_heartbeat=last_heartbeat,
                current_status=current_status,
                alert_count=alert_count,
                alert_severity=alert_severity,
                monitor_name=monitor_name,
                metrics_timestamp=now,
                created_at=now,
                updated_at=now,
            )
            db.add(metric)

        await db.commit()
        await db.refresh(metric)
        return metric

    async def bulk_upsert_metrics(
        self,
        db: AsyncSession,
        metrics_data: list[dict[str, Any]],
    ) -> int:
        """Bulk insert or update terminal metrics."""
        created_count = 0

        for data in metrics_data:
            await self.upsert_metric(db, **data)
            created_count += 1

        await db.commit()
        return created_count

    async def get_last_sync_time(
        self,
        db: AsyncSession,
        *,
        owner_username: str,
    ) -> datetime | None:
        """Get the last sync time for owner's terminals."""
        query = (
            select(func.max(TerminalMetric.metrics_timestamp))
            .where(TerminalMetric.owner_username == owner_username)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()


crud_terminal_metric = CRUDBerminalMetric(TerminalMetric)
