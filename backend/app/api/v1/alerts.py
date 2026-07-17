"""
Alert management API routes - Alertmanager Webhook.
"""

import json
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.config import settings
from app.core.audit.sanitizer import sanitize_sensitive_data
from app.core.logging import get_logger
from app.core.tz import now_shanghai
from app.crud.crud_alert import crud_alert_history, crud_alert_silence, crud_alert_template
from app.models.alert import AlertHistory, AlertHistoryStatus
from app.schemas.alert import AlertmanagerWebhookPayload
from app.services.alerts.alert_inhibition import alert_inhibition_service

router = APIRouter()
logger = get_logger(__name__)


@router.get(
    "/alert/stats",
    summary="获取告警统计信息",
    description="获取告警中心的统计数据，包括接收器、抑制规则、模板和告警数量",
)
async def get_alert_stats(
    db: AsyncSession = Depends(get_db),
):
    """Get alert statistics for the dashboard."""
    # Get silences count
    silences_result = await db.execute(select(func.count()).select_from(crud_alert_silence.model))
    total_silences = silences_result.scalar() or 0

    active_silences_result = await db.execute(
        select(func.count())
        .select_from(crud_alert_silence.model)
        .where(crud_alert_silence.model.is_active)
    )
    active_silences = active_silences_result.scalar() or 0

    # Get templates count
    templates_result = await db.execute(select(func.count()).select_from(crud_alert_template.model))
    total_templates = templates_result.scalar() or 0

    active_templates_result = await db.execute(
        select(func.count())
        .select_from(crud_alert_template.model)
        .where(crud_alert_template.model.is_active)
    )
    active_templates = active_templates_result.scalar() or 0

    # Get alert history stats
    history_result = await db.execute(select(func.count()).select_from(crud_alert_history.model))
    total_history = history_result.scalar() or 0

    firing_result = await db.execute(
        select(func.count())
        .select_from(crud_alert_history.model)
        .where(crud_alert_history.model.status == "firing")
    )
    firing_alerts = firing_result.scalar() or 0

    resolved_result = await db.execute(
        select(func.count())
        .select_from(crud_alert_history.model)
        .where(crud_alert_history.model.status == "resolved")
    )
    resolved_alerts = resolved_result.scalar() or 0

    return {
        "totalSilences": total_silences,
        "activeSilences": active_silences,
        "totalTemplates": total_templates,
        "activeTemplates": active_templates,
        "firingAlerts": firing_alerts,
        "resolvedAlerts": resolved_alerts,
        "totalHistory": total_history,
    }


def parse_alertmanager_datetime(dt_value: datetime | str | None) -> datetime | None:
    """Parse Alertmanager datetime string or datetime object to datetime object.

    Alertmanager uses ISO 8601 format with 'Z' suffix for UTC.
    Also handles the special case of '0001-01-01T00:00:00Z' which means no end time.
    """
    if dt_value is None:
        return None

    if isinstance(dt_value, datetime):
        return dt_value

    dt_str = str(dt_value)

    if not dt_str:
        return None

    if dt_str == "0001-01-01T00:00:00Z":
        return None

    try:
        dt_str = dt_str.replace("Z", "+00:00")
        return datetime.fromisoformat(dt_str)
    except ValueError:
        logger.warning(f"Failed to parse datetime: {dt_str}", extra={"action": "alert.receive"})
        return None


async def process_alert(
    db: AsyncSession,
    alert_data: dict[str, Any],
) -> dict[str, Any]:
    """Process a single alert from Alertmanager webhook.

    Args:
        db: Database session
        alert_data: Single alert data from Alertmanager payload

    Returns:
        Processing result with suppressed flag and history ID
    """
    alertname = alert_data.get("labels", {}).get("alertname", "Unknown")
    status_str = alert_data.get("status", "firing")
    severity = alert_data.get("labels", {}).get("severity", "info")
    labels = alert_data.get("labels", {})
    annotations = alert_data.get("annotations", {})
    starts_at = parse_alertmanager_datetime(alert_data.get("startsAt"))
    ends_at = parse_alertmanager_datetime(alert_data.get("endsAt"))

    # Map Alertmanager status to our status
    if status_str == "resolved":
        alert_status = AlertHistoryStatus.RESOLVED
    else:
        alert_status = AlertHistoryStatus.FIRING

    instance = labels.get("instance", "")

    # When resolved, batch-update all firing records with same alertname+instance+starts_at
    # I-01 修复:
    # 1. 加 starts_at 过滤，仅影响当前告警周期，避免误伤上一周期已 resolved 的记录
    # 2. 排除 SUPPRESSED 状态（被抑制的告警不应被 resolved webhook 批量改为 resolved，
    #    抑制规则由 alert_inhibition_service 管理）
    # 3. 显式过滤 status='firing'，避免误改已 resolved 的历史记录（原条件 status != RESOLVED
    #    会命中 SUPPRESSED，且语义模糊）
    # ND-2 修复（第二轮审查）：原 starts_at=None 时整个批量 resolve 块被跳过，
    # 旧 firing 记录状态保持 firing。Alertmanager 协议保证总会带 startsAt，
    # 但防御性处理：starts_at 为 None 时 fallback 使用当前时间，避免漏处理。
    if status_str == "resolved" and alertname and instance:
        effective_starts_at = starts_at if starts_at is not None else now_shanghai()
        try:
            pending_query = select(AlertHistory).where(
                and_(
                    AlertHistory.alertname == alertname,
                    AlertHistory.labels.op("->>")("instance") == instance,
                    AlertHistory.starts_at == effective_starts_at,
                    AlertHistory.status == AlertHistoryStatus.FIRING.value,
                )
            )
            pending_result = await db.execute(pending_query)
            pending_alerts = pending_result.scalars().all()
            if pending_alerts:
                now = now_shanghai()
                for pending in pending_alerts:
                    pending.status = AlertHistoryStatus.RESOLVED.value
                    pending.ends_at = now
                await db.commit()
                logger.info(
                    f"Batch resolved {len(pending_alerts)} firing alerts for "
                    f"alertname={alertname}, instance={instance}, starts_at={effective_starts_at}",
                    extra={
                        "action": "alert.resolve",
                        "alertname": alertname,
                        "instance": instance,
                        "starts_at": effective_starts_at.isoformat() if effective_starts_at else None,
                        "resolved_count": len(pending_alerts),
                    },
                )
        except Exception as exc:
            logger.warning(
                f"Failed to batch resolve pending alerts: {exc}",
                extra={"action": "alert.resolve", "error": str(exc)},
            )

    # Check if alert should be suppressed
    try:
        is_suppressed, silence_id = await alert_inhibition_service.check_alert_inhibition(
            db=db,
            alert_labels=labels,
        )
        logger.info(
            f"Inhibition check result: is_suppressed={is_suppressed}, silence_id={silence_id}",
            extra={
                "action": "alert.receive",
                "is_suppressed": is_suppressed,
                "silence_id": silence_id,
            },
        )
    except Exception as exc:
        logger.error(
            f"Error in inhibition check: {exc}",
            extra={"action": "alert.receive", "error": str(exc)},
        )
        is_suppressed, silence_id = False, None

    if is_suppressed:
        alert_status = AlertHistoryStatus.SUPPRESSED

    # Create or update alert history record
    try:
        logger.info(
            f"Processing history record: alertname={alertname}, status={alert_status.value}, severity={severity}",
            extra={
                "action": "alert.receive",
                "alertname": alertname,
                "status": alert_status.value,
                "severity": severity,
            },
        )

        # For firing alerts, check if a matching record already exists
        # (same alertname + instance + starts_at), regardless of current status.
        # This prevents duplicate records when alerts flap (firing→resolved→firing).
        # C-04 修复: 加 with_for_update() 行锁，减少并发 UPDATE 场景的冲突
        # 终极方案: 部分唯一索引 ix_alert_history_firing_unique 兜底并发 INSERT
        existing_record = None
        already_notified = False
        if alert_status == AlertHistoryStatus.FIRING and instance:
            existing_query = (
                select(AlertHistory)
                .where(
                    and_(
                        AlertHistory.alertname == alertname,
                        AlertHistory.labels.op("->>")("instance") == instance,
                        AlertHistory.starts_at == starts_at,
                    )
                )
                .order_by(AlertHistory.id.desc())
                .limit(1)
                .with_for_update()  # C-04: 行锁，锁定已存在的记录
            )
            existing_result = await db.execute(existing_query)
            existing_record = existing_result.scalar_one_or_none()
            # If the existing record was already notified, skip re-notification
            # to prevent duplicate cards during alert flapping.
            if existing_record and existing_record.notification_sent:
                already_notified = True

        if existing_record:
            # Update existing record instead of creating a duplicate
            existing_record.status = alert_status.value
            existing_record.severity = severity
            existing_record.labels = labels
            existing_record.annotations = annotations
            existing_record.is_suppressed = is_suppressed
            existing_record.silence_id = silence_id
            # Clear ends_at when reverting from resolved back to firing
            existing_record.ends_at = None
            await db.commit()
            await db.refresh(existing_record)
            history = existing_record
            logger.info(
                f"Updated existing history record: id={history.id}, already_notified={already_notified}",
                extra={"action": "alert.receive", "history_id": history.id, "already_notified": already_notified},
            )
        else:
            history = await crud_alert_history.create_from_alertmanager(
                db=db,
                alertname=alertname,
                status=alert_status.value,
                severity=severity,
                labels=labels,
                annotations=annotations,
                starts_at=starts_at or now_shanghai(),
                ends_at=ends_at,
                is_suppressed=is_suppressed,
                silence_id=silence_id,
            )
            logger.info(
                f"Created new history record: id={history.id}",
                extra={"action": "alert.receive", "history_id": history.id},
            )
    except Exception as exc:
        import traceback

        logger.error(
            f"Error creating history record: {exc}\n{traceback.format_exc()}",
            extra={"action": "alert.receive", "error": str(exc)},
        )
        raise

    # Prepare alert data for notification
    alert_notification_data = {
        "alertname": alertname,
        "status": status_str,
        "severity": severity,
        "instance": labels.get("instance", ""),
        "description": annotations.get("description", ""),
        "starts_at": starts_at.isoformat() if starts_at else now_shanghai().isoformat(),
        "labels": labels,
        "annotations": annotations,
        "is_suppressed": is_suppressed,
        "silence_id": silence_id,
        "history_id": history.id,
    }

    # Send notification asynchronously if not suppressed
    if not is_suppressed:
        # Skip notification if this alert instance was already notified
        # (prevents duplicate cards during alert flapping firing→resolved→firing)
        if already_notified:
            logger.info(
                f"Alert notification skipped (already notified for this instance): "
                f"{alertname}, instance={instance}, history_id={history.id}",
                extra={
                    "action": "alert.aggregate",
                    "alertname": alertname,
                    "instance": instance,
                    "history_id": history.id,
                    "reason": "already_notified",
                },
            )
            is_aggregated = True
            notification_ctx = None
        else:
            # Aggregation check: skip notification if same alertname+instance
            # was already notified within the aggregation window.
            # Note: status != RESOLVED is kept here — resolved records should NOT
            # suppress a genuinely new alert (different starts_at) that fires
            # within the window. The already_notified check above handles the
            # flap case (same starts_at) separately.
            aggregation_window = settings.alert_aggregation_window_seconds
            is_aggregated = False
            if aggregation_window > 0 and instance:
                window_start = now_shanghai() - timedelta(seconds=aggregation_window)
                agg_query = (
                    select(func.count(AlertHistory.id))
                    .where(
                        and_(
                            AlertHistory.alertname == alertname,
                            AlertHistory.labels.op("->>")("instance") == instance,
                            AlertHistory.notification_sent.is_(True),
                            AlertHistory.status != AlertHistoryStatus.RESOLVED.value,
                            AlertHistory.id != history.id,
                            AlertHistory.created_at >= window_start,
                        )
                    )
                )
                agg_result = await db.execute(agg_query)
                recent_count = agg_result.scalar() or 0
                if recent_count > 0:
                    is_aggregated = True
                    logger.info(
                        f"Alert aggregated (skipped notification): "
                        f"{alertname}, instance={instance}, "
                        f"recent_count={recent_count}, window={aggregation_window}s",
                        extra={
                            "action": "alert.aggregate",
                            "alertname": alertname,
                            "instance": instance,
                            "recent_count": recent_count,
                            "window_seconds": aggregation_window,
                        },
                    )

            if not is_aggregated:
                # 三阶段分离: 阶段 1 (prepare) 在 DB session 内完成所有 DB 操作
                # 阶段 2 (execute) 在 db_operation_with_retry 外执行飞书调用
                # 阶段 3 (save) 使用新 session 保存 message_id
                from app.services.alerts.notification_task import prepare_alert_notification

                notification_ctx = await prepare_alert_notification(db, alert_notification_data)
                if notification_ctx:
                    logger.info(
                        f"Alert notification prepared: {alertname}, history_id={history.id}",
                        extra={"action": "alert.receive", "alertname": alertname, "history_id": history.id},
                    )
                else:
                    logger.info(
                        f"Alert notification skipped (no recipients or template): "
                        f"{alertname}, history_id={history.id}",
                        extra={"action": "alert.receive", "alertname": alertname, "history_id": history.id},
                    )
            else:
                logger.info(
                    f"Alert notification skipped due to aggregation: "
                    f"{alertname}, history_id={history.id}",
                    extra={"action": "alert.aggregate", "alertname": alertname, "history_id": history.id},
                )
                notification_ctx = None
    else:
        logger.info(
            f"Alert suppressed by silence rule: {alertname}, silence_id={silence_id}",
            extra={"action": "alert.receive", "alertname": alertname, "silence_id": silence_id},
        )
        notification_ctx = None

    return {
        "history_id": history.id,
        "alertname": alertname,
        "status": alert_status.value,
        "is_suppressed": is_suppressed,
        "silence_id": silence_id,
        "is_aggregated": is_aggregated if not is_suppressed else False,
        # 三阶段分离: 返回 notification_ctx 供调用方执行飞书调用
        "notification_ctx": notification_ctx,
    }


@router.post(
    "/alert/webhook/alertmanager",
    status_code=status.HTTP_200_OK,
    summary="接收 Alertmanager 告警",
    description="""
    接收 Alertmanager Webhook 发送的告警通知。

    - 解析 Alertmanager v4 payload
    - 检查抑制规则
    - 渲染通知模板
    - 发送通知（异步）
    - 记录告警历史

    此接口无需认证，认证在 Alertmanager 端配置。
    """,
)
async def receive_alertmanager_webhook(
    request: Request,
    payload: AlertmanagerWebhookPayload,
    db: AsyncSession = Depends(get_db),
):
    """Receive Alertmanager webhook payload.

    This endpoint handles the Alertmanager v4 webhook format and processes
    alerts through the notification pipeline.
    """
    # I-04 修复: webhook payload 脱敏 + 截断到 500 字符
    # 1. 用 sanitize_sensitive_data 递归脱敏 labels/annotations 中的敏感字段
    #    (password/token/api_key/authorization 等 → 前后2字符+***)
    # 2. 截断到 500 字符，避免大 payload 占用日志空间
    try:
        sanitized_payload = sanitize_sensitive_data(payload.model_dump())
        payload_json = json.dumps(sanitized_payload, ensure_ascii=False, default=str)
        if len(payload_json) > 500:
            payload_json = payload_json[:500] + f"...(truncated, total={len(payload_json)})"
        logger.info(
            f"Webhook payload (sanitized): {payload_json}",
            extra={"action": "alert.receive"},
        )
    except Exception as exc:
        logger.warning(
            f"Failed to sanitize webhook payload: {exc}",
            extra={"action": "alert.receive", "error": str(exc)},
        )
    logger.info(
        f"Received Alertmanager webhook: receiver={payload.receiver}, "
        f"status={payload.status}, alerts_count={len(payload.alerts)}",
        extra={
            "action": "alert.receive",
            "receiver": payload.receiver,
            "status": payload.status,
            "alerts_count": len(payload.alerts),
        },
    )

    results = []
    for alert in payload.alerts:
        try:
            # 每个 alert 使用独立 DB session，避免单个 alert 失败导致
            # session 进 rollback 状态后污染后续 alert（PendingRollbackError）
            from app.db.session import db_operation_with_retry

            async def _process_op(session, alert_data=alert.model_dump()):
                return await process_alert(session, alert_data)

            result = await db_operation_with_retry(_process_op, max_retries=2, retry_delay=1.0)

            # 三阶段分离: 阶段 2 (execute) - 飞书调用（不持有 DB session）
            # 在 db_operation_with_retry 外执行，DB session 已释放
            notification_ctx = result.pop("notification_ctx", None)
            if notification_ctx:
                from app.services.alerts.notification_task import (
                    execute_feishu_notification,
                    save_notification_result,
                )

                feishu_result = await execute_feishu_notification(notification_ctx)

                # 阶段 3 (save) - 保存 message_id（新 DB session）
                # C-03 修复: 移除 contextlib.suppress 静默吞异常，
                # 改为 try/except + save_failed 标志，失败时记录 ERROR 日志
                # 并在 result 上设置 save_failed=True 供调用方感知
                if feishu_result.needs_save:
                    # B023 修复：通过默认参数绑定循环变量，避免闭包延迟绑定陷阱
                    async def _save_op(session, _ctx=notification_ctx, _result=feishu_result):
                        await save_notification_result(
                            session, _ctx, _result
                        )

                    try:
                        await db_operation_with_retry(
                            _save_op, max_retries=1, retry_delay=1.0
                        )
                    except Exception as save_exc:
                        import traceback as _tb

                        logger.error(
                            f"Failed to save notification result: "
                            f"alertname={result.get('alertname')}, "
                            f"history_id={result.get('history_id')}, "
                            f"error={save_exc}\n{_tb.format_exc()}",
                            extra={
                                "action": "alert.receive",
                                "alertname": result.get("alertname"),
                                "history_id": result.get("history_id"),
                                "save_failed": True,
                                "error": str(save_exc),
                            },
                        )
                        result["save_failed"] = True

                logger.info(
                    f"Alert notification sent: {result.get('alertname')}, "
                    f"history_id={result.get('history_id')}, "
                    f"save_failed={result.get('save_failed', False)}",
                    extra={
                        "action": "alert.receive",
                        "alertname": result.get("alertname"),
                        "history_id": result.get("history_id"),
                        "save_failed": result.get("save_failed", False),
                    },
                )

            results.append(result)
        except Exception as exc:
            import traceback

            error_trace = traceback.format_exc()
            logger.error(
                f"Failed to process alert: {str(exc)}\n{error_trace}",
                extra={"action": "alert.receive", "error": str(exc)},
            )
            results.append(
                {
                    "error": str(exc),
                    "error_detail": error_trace,
                    "alert": alert.model_dump(),
                }
            )

    # Count results
    suppressed_count = sum(1 for r in results if r.get("is_suppressed"))
    firing_count = sum(1 for r in results if r.get("status") == "firing")
    resolved_count = sum(1 for r in results if r.get("status") == "resolved")
    error_count = sum(1 for r in results if r.get("error"))

    logger.info(
        f"Alertmanager webhook processed: "
        f"total={len(results)}, firing={firing_count}, "
        f"resolved={resolved_count}, suppressed={suppressed_count}, errors={error_count}",
        extra={
            "action": "alert.receive",
            "total": len(results),
            "firing": firing_count,
            "resolved": resolved_count,
            "suppressed": suppressed_count,
            "errors": error_count,
        },
    )

    return {
        "status": "success",
        "received_at": now_shanghai().isoformat(),
        "total_alerts": len(payload.alerts),
        "processed": {
            "firing": firing_count,
            "resolved": resolved_count,
            "suppressed": suppressed_count,
            "errors": error_count,
        },
        "results": results,
    }
