"""
Monitoring and alerting API routes.
"""
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_permissions
from app.core.audit import audit_log
from app.core.exceptions import NotFoundError
from app.crud.base import CRUDBase
from app.models.monitor import Alert, AlertRule, Monitor, NotificationChannel
from app.schemas.monitor import (
    AlertAction,
    AlertListResponse,
    AlertResponse,
    AlertRuleCreate,
    AlertRuleResponse,
    AlertRuleUpdate,
    MonitorCreate,
    MonitorListResponse,
    MonitorResponse,
    MonitorUpdate,
    NotificationChannelCreate,
    NotificationChannelResponse,
    NotificationChannelUpdate,
)

router = APIRouter(prefix="/monitor")

crud_monitor = CRUDBase(Monitor)
crud_alert = CRUDBase(Alert)
crud_alert_rule = CRUDBase(AlertRule)
crud_notification_channel = CRUDBase(NotificationChannel)


@router.get("/monitors", response_model=MonitorListResponse)
async def list_monitors(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    monitor_type: str | None = Query(None),
    status: str | None = Query(None),
    is_enabled: bool | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=require_permissions(["monitor:read"]),
):
    """List all monitors with filters."""
    query = select(Monitor)

    filters = []
    if monitor_type:
        filters.append(Monitor.monitor_type == monitor_type)
    if status:
        filters.append(Monitor.current_status == status)
    if is_enabled is not None:
        filters.append(Monitor.is_enabled == is_enabled)

    if filters:
        query = query.where(and_(*filters))

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()

    return {"total": total, "items": items}


@router.post("/monitors", response_model=MonitorResponse, status_code=status.HTTP_201_CREATED)
@audit_log(operation_type="CREATE", module="monitor", object_type="Monitor")
async def create_monitor(
    request: Request,
    obj_in: MonitorCreate,
    db: AsyncSession = Depends(get_db),
    current_user=require_permissions(["monitor:write"]),
):
    """Create a new monitor."""
    monitor = await crud_monitor.create(db, obj_in=obj_in)
    return monitor


@router.get("/monitors/{monitor_id}", response_model=MonitorResponse)
async def get_monitor(
    monitor_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=require_permissions(["monitor:read"]),
):
    """Get monitor by ID."""
    monitor = await crud_monitor.get(db, id=monitor_id)
    if not monitor:
        raise NotFoundError(detail=f"Monitor with ID {monitor_id} not found")
    return monitor


@router.put("/monitors/{monitor_id}", response_model=MonitorResponse)
@audit_log(operation_type="UPDATE", module="monitor", object_type="Monitor")
async def update_monitor(
    request: Request,
    monitor_id: int,
    obj_in: MonitorUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=require_permissions(["monitor:write"]),
):
    """Update monitor."""
    monitor = await crud_monitor.get(db, id=monitor_id)
    if not monitor:
        raise NotFoundError(detail=f"Monitor with ID {monitor_id} not found")

    monitor = await crud_monitor.update(db, db_obj=monitor, obj_in=obj_in)
    return monitor


@router.delete("/monitors/{monitor_id}", status_code=status.HTTP_204_NO_CONTENT)
@audit_log(operation_type="DELETE", module="monitor", object_type="Monitor")
async def delete_monitor(
    request: Request,
    monitor_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=require_permissions(["monitor:delete"]),
):
    """Delete monitor."""
    monitor = await crud_monitor.get(db, id=monitor_id)
    if not monitor:
        raise NotFoundError(detail=f"Monitor with ID {monitor_id} not found")

    await crud_monitor.delete(db, id=monitor_id)
    return None


@router.post("/monitors/{monitor_id}/toggle")
@audit_log(operation_type="UPDATE", module="monitor", object_type="Monitor")
async def toggle_monitor(
    request: Request,
    monitor_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=require_permissions(["monitor:write"]),
):
    """Toggle monitor enabled status."""
    monitor = await crud_monitor.get(db, id=monitor_id)
    if not monitor:
        raise NotFoundError(detail=f"Monitor with ID {monitor_id} not found")

    monitor.is_enabled = not monitor.is_enabled
    await db.commit()
    await db.refresh(monitor)
    return {"id": monitor_id, "is_enabled": monitor.is_enabled}


@router.get("/alerts", response_model=AlertListResponse)
async def list_alerts(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    severity: str | None = Query(None),
    monitor_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=require_permissions(["monitor:read"]),
):
    """List all alerts with filters."""
    query = select(Alert)

    filters = []
    if status:
        filters.append(Alert.status == status)
    if severity:
        filters.append(Alert.severity == severity)
    if monitor_id:
        filters.append(Alert.monitor_id == monitor_id)

    if filters:
        query = query.where(and_(*filters))

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    query = query.offset(skip).limit(limit).order_by(Alert.started_at.desc())
    result = await db.execute(query)
    alerts = result.scalars().all()

    return {"total": total, "items": alerts}


@router.get("/alerts/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=require_permissions(["monitor:read"]),
):
    """Get alert by ID."""
    alert = await crud_alert.get(db, id=alert_id)
    if not alert:
        raise NotFoundError(detail=f"Alert with ID {alert_id} not found")
    return alert


@router.post("/alerts/{alert_id}/action", response_model=AlertResponse)
@audit_log(operation_type="UPDATE", module="monitor", object_type="Alert")
async def alert_action(
    request: Request,
    alert_id: int,
    action: AlertAction,
    db: AsyncSession = Depends(get_db),
    current_user=require_permissions(["monitor:write"]),
):
    """Perform action on alert (acknowledge, resolve, suppress)."""
    alert = await crud_alert.get(db, id=alert_id)
    if not alert:
        raise NotFoundError(detail=f"Alert with ID {alert_id} not found")

    now = datetime.utcnow()

    if action.action == "acknowledge":
        alert.status = "acknowledged"
        alert.acknowledged_at = now
        alert.acknowledged_by = current_user.id
    elif action.action == "resolve":
        alert.status = "resolved"
        alert.resolved_at = now
        alert.resolved_by = current_user.id
    elif action.action == "suppress":
        alert.status = "suppressed"

    await db.commit()
    await db.refresh(alert)
    return alert


@router.get("/alert-rules", response_model=list[AlertRuleResponse])
async def list_alert_rules(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    is_enabled: bool | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=require_permissions(["monitor:read"]),
):
    """List all alert rules."""
    query = select(AlertRule)

    if is_enabled is not None:
        query = query.where(AlertRule.is_enabled == is_enabled)

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    rules = result.scalars().all()
    return rules


@router.post("/alert-rules", response_model=AlertRuleResponse, status_code=status.HTTP_201_CREATED)
@audit_log(operation_type="CREATE", module="monitor", object_type="AlertRule")
async def create_alert_rule(
    request: Request,
    obj_in: AlertRuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user=require_permissions(["monitor:write"]),
):
    """Create a new alert rule."""
    rule = await crud_alert_rule.create(db, obj_in=obj_in)
    return rule


@router.get("/alert-rules/{rule_id}", response_model=AlertRuleResponse)
async def get_alert_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=require_permissions(["monitor:read"]),
):
    """Get alert rule by ID."""
    rule = await crud_alert_rule.get(db, id=rule_id)
    if not rule:
        raise NotFoundError(detail=f"Alert rule with ID {rule_id} not found")
    return rule


@router.put("/alert-rules/{rule_id}", response_model=AlertRuleResponse)
@audit_log(operation_type="UPDATE", module="monitor", object_type="AlertRule")
async def update_alert_rule(
    request: Request,
    rule_id: int,
    obj_in: AlertRuleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=require_permissions(["monitor:write"]),
):
    """Update alert rule."""
    rule = await crud_alert_rule.get(db, id=rule_id)
    if not rule:
        raise NotFoundError(detail=f"Alert rule with ID {rule_id} not found")

    rule = await crud_alert_rule.update(db, db_obj=rule, obj_in=obj_in)
    return rule


@router.delete("/alert-rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
@audit_log(operation_type="DELETE", module="monitor", object_type="AlertRule")
async def delete_alert_rule(
    request: Request,
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=require_permissions(["monitor:delete"]),
):
    """Delete alert rule."""
    rule = await crud_alert_rule.get(db, id=rule_id)
    if not rule:
        raise NotFoundError(detail=f"Alert rule with ID {rule_id} not found")

    await crud_alert_rule.delete(db, id=rule_id)
    return None


@router.get("/notification-channels", response_model=list[NotificationChannelResponse])
async def list_notification_channels(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user=require_permissions(["monitor:read"]),
):
    """List all notification channels."""
    channels = await crud_notification_channel.get_multi(db, skip=skip, limit=limit)
    return channels


@router.post("/notification-channels", response_model=NotificationChannelResponse, status_code=status.HTTP_201_CREATED)
@audit_log(operation_type="CREATE", module="monitor", object_type="NotificationChannel")
async def create_notification_channel(
    request: Request,
    obj_in: NotificationChannelCreate,
    db: AsyncSession = Depends(get_db),
    current_user=require_permissions(["monitor:write"]),
):
    """Create a new notification channel."""
    channel = await crud_notification_channel.create(db, obj_in=obj_in)
    return channel


@router.get("/notification-channels/{channel_id}", response_model=NotificationChannelResponse)
async def get_notification_channel(
    channel_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=require_permissions(["monitor:read"]),
):
    """Get notification channel by ID."""
    channel = await crud_notification_channel.get(db, id=channel_id)
    if not channel:
        raise NotFoundError(detail=f"Notification channel with ID {channel_id} not found")
    return channel


@router.put("/notification-channels/{channel_id}", response_model=NotificationChannelResponse)
@audit_log(operation_type="UPDATE", module="monitor", object_type="NotificationChannel")
async def update_notification_channel(
    request: Request,
    channel_id: int,
    obj_in: NotificationChannelUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=require_permissions(["monitor:write"]),
):
    """Update notification channel."""
    channel = await crud_notification_channel.get(db, id=channel_id)
    if not channel:
        raise NotFoundError(detail=f"Notification channel with ID {channel_id} not found")

    channel = await crud_notification_channel.update(db, db_obj=channel, obj_in=obj_in)
    return channel


@router.delete("/notification-channels/{channel_id}", status_code=status.HTTP_204_NO_CONTENT)
@audit_log(operation_type="DELETE", module="monitor", object_type="NotificationChannel")
async def delete_notification_channel(
    request: Request,
    channel_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=require_permissions(["monitor:delete"]),
):
    """Delete notification channel."""
    channel = await crud_notification_channel.get(db, id=channel_id)
    if not channel:
        raise NotFoundError(detail=f"Notification channel with ID {channel_id} not found")

    await crud_notification_channel.delete(db, id=channel_id)
    return None


@router.post("/notification-channels/{channel_id}/test")
@audit_log(operation_type="EXPORT", module="monitor", object_type="NotificationChannel")
async def test_notification_channel(
    request: Request,
    channel_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=require_permissions(["monitor:write"]),
):
    """Test notification channel."""
    channel = await crud_notification_channel.get(db, id=channel_id)
    if not channel:
        raise NotFoundError(detail=f"Notification channel with ID {channel_id} not found")

    channel.last_test_at = datetime.utcnow()
    channel.last_test_status = "success"
    await db.commit()
    await db.refresh(channel)

    return {"id": channel_id, "test_status": channel.last_test_status}
