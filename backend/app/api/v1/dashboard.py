"""
Dashboard API routes for terminal metrics and overview statistics.
"""

import asyncio

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.crud import crud_terminal_metric
from app.models.alert import AlertHistory
from app.models.asset import Asset, AssetType
from app.models.it_feedback import ITFeedback
from app.models.ops import Certificate, CertificateStatus, Deployment
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


async def _get_alert_stats(db: AsyncSession) -> dict:
    """Query alert statistics using SQL aggregation."""
    firing_count_stmt = (
        select(func.count()).select_from(AlertHistory).where(AlertHistory.status == "firing")
    )
    resolved_count_stmt = (
        select(func.count()).select_from(AlertHistory).where(AlertHistory.status == "resolved")
    )
    recent_alerts_stmt = (
        select(
            AlertHistory.alertname,
            AlertHistory.severity,
            AlertHistory.status,
            AlertHistory.starts_at,
            AlertHistory.labels,
        )
        .order_by(AlertHistory.starts_at.desc())
        .limit(5)
    )

    firing_count, resolved_count, recent_rows = await asyncio.gather(
        db.scalar(firing_count_stmt),
        db.scalar(resolved_count_stmt),
        db.execute(recent_alerts_stmt),
    )

    recent_alerts = [
        {
            "alertname": row.alertname,
            "severity": row.severity,
            "status": row.status,
            "starts_at": row.starts_at.isoformat() if row.starts_at else None,
            "instance": row.labels.get("instance") if row.labels else None,
        }
        for row in recent_rows.all()
    ]

    return {
        "firing_count": firing_count or 0,
        "resolved_count": resolved_count or 0,
        "recent_alerts": recent_alerts,
    }


async def _get_it_feedback_stats(db: AsyncSession) -> dict:
    """Query IT feedback statistics using SQL aggregation."""
    pending_stmt = (
        select(func.count()).select_from(ITFeedback).where(ITFeedback.status == "pending")
    )
    handling_stmt = (
        select(func.count()).select_from(ITFeedback).where(ITFeedback.status == "handling")
    )
    resolved_stmt = (
        select(func.count()).select_from(ITFeedback).where(ITFeedback.status == "resolved")
    )

    pending_count, handling_count, resolved_count = await asyncio.gather(
        db.scalar(pending_stmt),
        db.scalar(handling_stmt),
        db.scalar(resolved_stmt),
    )

    return {
        "pending_count": pending_count or 0,
        "handling_count": handling_count or 0,
        "resolved_count": resolved_count or 0,
    }


async def _get_asset_stats(db: AsyncSession) -> dict:
    """Query asset statistics using SQL aggregation."""
    total_stmt = select(func.count()).select_from(Asset)
    server_stmt = (
        select(func.count()).select_from(Asset).where(Asset.asset_type == AssetType.SERVER)
    )
    domain_stmt = (
        select(func.count()).select_from(Asset).where(Asset.asset_type == AssetType.NETWORK)
    )
    terminal_stmt = (
        select(func.count()).select_from(Asset).where(Asset.asset_type == AssetType.TERMINAL)
    )

    total_count, server_count, domain_count, terminal_count = await asyncio.gather(
        db.scalar(total_stmt),
        db.scalar(server_stmt),
        db.scalar(domain_stmt),
        db.scalar(terminal_stmt),
    )

    return {
        "total_count": total_count or 0,
        "server_count": server_count or 0,
        "domain_count": domain_count or 0,
        "terminal_count": terminal_count or 0,
    }


async def _get_cert_stats(db: AsyncSession) -> dict:
    """Query certificate statistics using SQL aggregation."""
    total_stmt = select(func.count()).select_from(Certificate)
    valid_stmt = (
        select(func.count())
        .select_from(Certificate)
        .where(Certificate.status == CertificateStatus.ACTIVE)
    )
    expiring_stmt = (
        select(func.count())
        .select_from(Certificate)
        .where(Certificate.status == CertificateStatus.EXPIRING)
    )
    expired_stmt = (
        select(func.count())
        .select_from(Certificate)
        .where(Certificate.status == CertificateStatus.EXPIRED)
    )

    total_count, valid_count, expiring_count, expired_count = await asyncio.gather(
        db.scalar(total_stmt),
        db.scalar(valid_stmt),
        db.scalar(expiring_stmt),
        db.scalar(expired_stmt),
    )

    return {
        "total_count": total_count or 0,
        "valid_count": valid_count or 0,
        "expiring_count": expiring_count or 0,
        "expired_count": expired_count or 0,
    }


async def _get_recent_deployments(db: AsyncSession) -> list[dict]:
    """Query recent 5 deployment records."""
    stmt = (
        select(
            Deployment.project_name,
            Deployment.environment,
            Deployment.status,
            Deployment.created_at,
        )
        .order_by(Deployment.created_at.desc())
        .limit(5)
    )
    result = await db.execute(stmt)

    return [
        {
            "project_name": row.project_name,
            "environment": row.environment,
            "status": row.status,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in result.all()
    ]


@router.get("/dashboard/overview")
async def get_dashboard_overview(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get dashboard overview with all statistics.

    Returns aggregated statistics for alerts, IT feedback, assets,
    certificates, and recent deployments.
    """
    (
        alert_stats,
        it_feedback_stats,
        asset_stats,
        cert_stats,
        recent_deployments,
    ) = await asyncio.gather(
        _get_alert_stats(db),
        _get_it_feedback_stats(db),
        _get_asset_stats(db),
        _get_cert_stats(db),
        _get_recent_deployments(db),
    )

    return {
        "alert_stats": alert_stats,
        "it_feedback_stats": it_feedback_stats,
        "asset_stats": asset_stats,
        "cert_stats": cert_stats,
        "recent_deployments": recent_deployments,
    }
