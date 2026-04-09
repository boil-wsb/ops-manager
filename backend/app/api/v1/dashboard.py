"""
Dashboard API routes for terminal metrics.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.crud import crud_terminal_metric
from app.models.user import User

router = APIRouter()


@router.get("/dashboard/my-terminal-metrics")
async def get_my_terminal_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get terminal metrics dashboard for current user.

    Returns summary statistics and detailed terminal metrics for the logged-in user.
    """
    owner_username = current_user.username

    summary = await crud_terminal_metric.get_summary_by_owner(db, owner_username=owner_username)

    terminals = await crud_terminal_metric.get_multi_by_owner(
        db, owner_username=owner_username, skip=0, limit=100
    )

    last_sync_time = await crud_terminal_metric.get_last_sync_time(
        db, owner_username=owner_username
    )

    return {
        "summary": summary,
        "terminals": [
            {
                "id": t.id,
                "asset_id": t.asset_id,
                "hostname": t.hostname,
                "ip_address": t.ip_address,
                "cpu_usage": t.cpu_usage,
                "memory_usage": t.memory_usage,
                "memory_total_gb": t.memory_total_gb,
                "disk_usage": t.disk_usage,
                "disk_total_gb": t.disk_total_gb,
                "network_in": t.network_in,
                "network_out": t.network_out,
                "uptime_hours": t.uptime_hours,
                "current_status": t.current_status,
                "alert_count": t.alert_count,
                "alert_severity": t.alert_severity,
                "monitor_name": t.monitor_name,
                "last_heartbeat": t.last_heartbeat.isoformat() if t.last_heartbeat else None,
            }
            for t in terminals
        ],
        "last_sync_time": last_sync_time.isoformat() if last_sync_time else None,
    }
