"""
Alert notification service.
"""

import re
from datetime import datetime
from typing import Any

from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.tz import now_shanghai
from app.models.alert import AlertTemplate
from app.models.asset import Asset
from app.models.user import User
from app.services.alerts.alert_inhibition import alert_inhibition_service
from app.services.alerts.alert_template import alert_template_service
from app.services.alerts.feishu_notification import get_feishu_notification_service

logger = get_logger(__name__)


async def send_alert_notification(
    alert_data: dict[str, Any],
    db: AsyncSession,
) -> None:
    """Send alert notification to asset owner based on instance IP.

    Args:
        alert_data: Alert data dictionary containing:
            - alertname: str
            - status: str (firing/resolved)
            - severity: str
            - instance: str
            - description: str
            - starts_at: str (ISO format)
            - labels: dict
            - annotations: dict
            - is_suppressed: bool
            - silence_id: int | None
        db: Database session
    """
    try:
        instance = alert_data.get("instance", "")
        if not instance:
            logger.info("告警无实例信息，跳过通知", extra={"action": "alert.notify"})
            return

        email_templates_result = await db.execute(
            select(AlertTemplate)
            .where(
                AlertTemplate.template_type == "email",
                AlertTemplate.is_active.is_(True),
            )
            .order_by(case((AlertTemplate.is_default.is_(True), 0), else_=1))
        )
        email_templates = list(email_templates_result.scalars().all())

        feishu_templates_result = await db.execute(
            select(AlertTemplate)
            .where(
                AlertTemplate.template_type == "feishu",
                AlertTemplate.is_active.is_(True),
            )
            .order_by(case((AlertTemplate.is_default.is_(True), 0), else_=1))
        )
        feishu_templates = list(feishu_templates_result.scalars().all())

        await _send_notification_by_instance(
            db=db,
            instance=instance,
            alert_data=alert_data,
            email_templates=email_templates,
            feishu_templates=feishu_templates,
        )

        logger.info(
            f"告警通知已处理: alertname={alert_data.get('alertname')}, instance={instance}",
            extra={"action": "alert.notify", "alertname": alert_data.get('alertname'), "instance": instance},
        )

    except Exception as exc:
        logger.error(f"处理告警通知失败: {str(exc)}", extra={"action": "alert.notify"})
        raise


async def _send_notification_by_instance(
    db: AsyncSession,
    instance: str,
    alert_data: dict[str, Any],
    email_templates: list[AlertTemplate],
    feishu_templates: list[AlertTemplate],
) -> None:
    """Send notification to asset owner by instance IP.

    Args:
        db: Database session
        instance: Instance identifier (usually IP address)
        alert_data: Alert data dictionary
        email_templates: List of active email templates
        feishu_templates: List of active feishu templates
    """
    alertname = alert_data.get("alertname", "")
    status = alert_data.get("status", "firing")
    severity = alert_data.get("severity", "info")
    description = alert_data.get("description", "")
    starts_at_str = alert_data.get("starts_at", "")
    labels = alert_data.get("labels", {})
    annotations = alert_data.get("annotations", {})

    logger.info(f"收到告警数据: {alert_data}", extra={"action": "alert.notify"})

    starts_at = starts_at_str
    if isinstance(starts_at_str, str):
        try:
            starts_at = datetime.fromisoformat(starts_at_str.replace("Z", "+00:00"))
        except ValueError:
            starts_at = now_shanghai()

    email_template = None
    feishu_template = None

    for template in email_templates:
        if template.is_default:
            email_template = template
            break
        elif template.is_active and email_template is None:
            email_template = template

    for template in feishu_templates:
        if template.is_default:
            feishu_template = template
            break
        elif template.is_active and feishu_template is None:
            feishu_template = template

    if email_template:
        logger.info(
            f"邮件模板匹配: id={email_template.id}, name={email_template.name}",
            extra={"action": "alert.notify", "template_id": email_template.id},
        )
        subject, body = await alert_template_service.render_alert_template(
            db=db,
            template=email_template,
            alertname=alertname,
            status=status,
            severity=severity,
            instance=instance,
            description=description,
            starts_at=starts_at,
            labels=labels,
            annotations=annotations,
        )

        if subject and body:
            logger.info(f"邮件通知已准备: instance={instance}, subject={subject}", extra={"action": "alert.notify", "instance": instance})

    if feishu_template:
        logger.info(
            f"飞书模板匹配: id={feishu_template.id}, name={feishu_template.name}",
            extra={"action": "alert.notify", "template_id": feishu_template.id},
        )
        logger.info(
            f"飞书模板内容 - subject_template: {feishu_template.subject_template}",
            extra={"action": "alert.notify"},
        )
        logger.info(
            f"飞书模板内容 - body_template: {feishu_template.body_template}",
            extra={"action": "alert.notify"},
        )
        subject, body = await alert_template_service.render_alert_template(
            db=db,
            template=feishu_template,
            alertname=alertname,
            status=status,
            severity=severity,
            instance=instance,
            description=description,
            starts_at=starts_at,
            labels=labels,
            annotations=annotations,
        )

        if body:
            starts_at_str = (
                starts_at.strftime("%Y-%m-%d %H:%M:%S")
                if isinstance(starts_at, datetime)
                else str(starts_at)
            )

            asset_owner_open_id = await _get_asset_owner_open_id(db, instance)
            if asset_owner_open_id:
                feishu_svc = get_feishu_notification_service()

                card = None
                if feishu_template and feishu_template.card_config:
                    starts_at_str = (
                        starts_at.strftime("%Y-%m-%d %H:%M:%S")
                        if isinstance(starts_at, datetime)
                        else str(starts_at)
                    )

                    external_url = labels.get("externalURL", annotations.get("externalURL", ""))
                    alerts_list = alert_data.get("alerts", [{}])
                    first_alert = alerts_list[0] if alerts_list else {}

                    context = {
                        "alertname": alertname,
                        "Alertname": alertname,
                        "alertId": f"{alertname}_{instance}".replace(".", "_").replace(":", "_"),
                        "status": status,
                        "Status": status,
                        "severity": severity,
                        "Severity": severity,
                        "instance": instance,
                        "Instance": instance,
                        "description": description,
                        "Description": description,
                        "starts_at": starts_at_str,
                        "startsAt": starts_at_str,
                        "StartsAt": starts_at_str,
                        "labels": labels,
                        "annotations": annotations,
                        "externalURL": external_url,
                        "alerts": alerts_list,
                        "firstAlert": first_alert,
                    }
                    import json

                    card_config_json = json.dumps(feishu_template.card_config)
                    rendered_card_str = alert_template_service.render_template(
                        template_str=card_config_json,
                        context=context,
                    )
                    logger.info(f"渲染卡片配置: {rendered_card_str[:500]}", extra={"action": "alert.notify"})
                    card = json.loads(rendered_card_str)
                    logger.info("使用模板card_config", extra={"action": "alert.notify"})

                if not card:
                    card = feishu_svc.build_alert_card(
                        alertname=alertname,
                        status=status,
                        severity=severity,
                        instance=instance,
                        description=description,
                        starts_at=starts_at_str,
                        env=labels.get("env"),
                    )
                    logger.info("使用默认build_alert_card", extra={"action": "alert.notify"})

                logger.info(f"飞书卡片JSON内容: {card}", extra={"action": "alert.notify"})

                if status == "resolved":
                    await _update_resolved_alert_card(
                        db=db,
                        alertname=alertname,
                        instance=instance,
                        severity=severity,
                    )
                else:
                    result = feishu_svc.send_p2p_card_message(
                        open_id=asset_owner_open_id,
                        card_content=card,
                    )
                    if result.get("success"):
                        message_id = result.get("message_id")
                        if message_id:
                            await _save_firing_alert_message_id(
                                db=db,
                                alertname=alertname,
                                instance=instance,
                                severity=severity,
                                message_id=message_id,
                            )
                        await _update_alert_history_notification_sent(
                            db=db,
                            alertname=alertname,
                            instance=instance,
                        )
                        logger.info(f"P2P飞书卡片已发送: instance={instance}", extra={"action": "alert.notify", "instance": instance})
                    else:
                        logger.warning(
                            f"P2P飞书卡片发送失败: instance={instance}",
                            extra={"action": "alert.notify", "instance": instance},
                        )
            else:
                logger.info(
                    f"未找到资产负责人: instance={instance}，跳过飞书通知",
                    extra={"action": "alert.notify", "instance": instance},
                )


async def _save_firing_alert_message_id(
    db: AsyncSession,
    alertname: str,
    instance: str,
    severity: str,
    message_id: str,
) -> None:
    """Save the Feishu message_id for a firing alert to AlertHistory.

    Args:
        db: Database session
        alertname: Alert name
        instance: Instance identifier
        severity: Alert severity
        message_id: Feishu open_message_id
    """
    from sqlalchemy import text

    try:
        result = await db.execute(
            text(
                "SELECT id FROM alert_history WHERE alertname = :name AND labels->>'instance' = :instance AND status = 'firing' ORDER BY id DESC LIMIT 1"
            ),
            {"name": alertname, "instance": instance},
        )
        row = result.fetchone()

        if row:
            history_id = row[0]
            await db.execute(
                text("UPDATE alert_history SET feishu_open_message_id = :msg_id WHERE id = :id"),
                {"msg_id": message_id, "id": history_id},
            )
            await db.commit()
            logger.info(
                f"保存feishu_open_message_id: alertname={alertname}, instance={instance}, history_id={history_id}",
                extra={"action": "alert.notify", "alertname": alertname, "instance": instance, "history_id": history_id},
            )
        else:
            logger.warning(
                f"未找到firing告警记录: alertname={alertname}, instance={instance}",
                extra={"action": "alert.notify", "alertname": alertname, "instance": instance},
            )

    except Exception as exc:
        logger.error(f"保存feishu_open_message_id异常: {str(exc)}", extra={"action": "alert.notify"})


async def _update_resolved_alert_card(
    db: AsyncSession,
    alertname: str,
    instance: str,
    severity: str,
) -> None:
    """Update the Feishu card for a resolved alert.

    Finds the corresponding firing alert's card and updates it to show 'resolved' status.

    Args:
        db: Database session
        alertname: Alert name
        instance: Instance identifier
        severity: Alert severity
    """
    from sqlalchemy import text

    try:
        result = await db.execute(
            text(
                "SELECT id, feishu_open_message_id FROM alert_history WHERE alertname = :name AND labels->>'instance' = :instance AND status = 'firing' AND feishu_open_message_id IS NOT NULL"
            ),
            {"name": alertname, "instance": instance},
        )
        row = result.fetchone()

        if not row:
            logger.warning(
                f"未找到firing告警卡片: alertname={alertname}, instance={instance}",
                extra={"action": "alert.resolve", "alertname": alertname, "instance": instance},
            )
            return

        history_id, feishu_open_message_id = row[0], row[1]

        feishu_svc = get_feishu_notification_service()
        resolved_card = feishu_svc.build_resolved_card(
            alertname=alertname,
            severity=severity,
            instance=instance,
        )

        update_result = feishu_svc.update_card_message(
            open_message_id=feishu_open_message_id,
            card_content=resolved_card,
        )

        if update_result.get("success"):
            await db.execute(
                text(
                    "UPDATE alert_history SET status = 'resolved', notification_sent = True WHERE id = :id"
                ),
                {"id": history_id},
            )
            await db.commit()
            logger.info(f"卡片已更新为resolved: alertname={alertname}, instance={instance}", extra={"action": "alert.resolve", "alertname": alertname, "instance": instance})
        else:
            logger.error(f"更新卡片失败: {update_result.get('message')}", extra={"action": "alert.resolve"})

    except Exception as exc:
        logger.error(f"更新resolved告警卡片异常: {str(exc)}", extra={"action": "alert.resolve"})


async def _update_alert_history_notification_sent(
    db: AsyncSession,
    alertname: str,
    instance: str,
) -> None:
    """Update AlertHistory.notification_sent to True for a specific alert.

    Args:
        db: Database session
        alertname: Alert name
        instance: Instance identifier
    """
    from sqlalchemy import text

    try:
        result = await db.execute(
            text(
                "SELECT id FROM alert_history WHERE alertname = :name AND labels->>'instance' = :instance AND status = 'firing'"
            ),
            {"name": alertname, "instance": instance},
        )
        row = result.fetchone()

        if row:
            history_id = row[0]
            await db.execute(
                text("UPDATE alert_history SET notification_sent = True WHERE id = :id"),
                {"id": history_id},
            )
            await db.commit()
            logger.info(
                f"更新notification_sent=True: id={history_id}, alertname={alertname}, instance={instance}",
                extra={"action": "alert.notify", "alertname": alertname, "instance": instance},
            )
        else:
            logger.warning(
                f"未找到firing告警记录(notification_sent): alertname={alertname}, instance={instance}",
                extra={"action": "alert.notify", "alertname": alertname, "instance": instance},
            )

    except Exception as exc:
        logger.error(f"更新notification_sent异常: {str(exc)}", extra={"action": "alert.notify"})


async def _get_asset_owner_open_id(db: AsyncSession, instance: str) -> str | None:
    """Get asset owner feishu_open_id by instance IP address.

    Args:
        db: Database session
        instance: Instance identifier (usually IP address)

    Returns:
        Feishu open_id of asset owner or None if not found
    """
    if not instance:
        return None

    ip_pattern = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
    if not ip_pattern.match(instance):
        return None

    try:
        result = await db.execute(
            select(Asset, User)
            .join(User, Asset.owner_id == User.id)
            .where(Asset.ip_address == instance)
        )
        row = result.first()

        if row:
            asset, user = row
            if user.feishu_open_id:
                logger.info(
                    f"找到资产负责人: asset={asset.name}, user={user.username}, open_id={user.feishu_open_id}",
                    extra={"action": "alert.notify", "instance": instance, "asset_name": asset.name, "username": user.username},
                )
                return user.feishu_open_id

        logger.debug(f"未找到资产负责人: IP={instance}", extra={"action": "alert.notify", "instance": instance})
        return None

    except Exception as exc:
        logger.error(f"查询资产负责人异常: {instance}: {str(exc)}", extra={"action": "alert.notify", "instance": instance})
        return None


def check_silence_expiry():
    """Periodic task to check and deactivate expired silence rules.

    This should be run periodically (e.g., every minute) to ensure
    expired silence rules are properly handled.
    """
    logger.info("检查过期静默规则...", extra={"action": "alert.silence"})

    alert_inhibition_service.clear_cache()
    logger.info("静默缓存已清理", extra={"action": "alert.silence"})


def cleanup_notification_cache():
    """Periodic task to clean up template and other caches."""
    logger.info("清理通知缓存...", extra={"action": "alert.notify"})
    alert_template_service.clear_cache()
    alert_inhibition_service.clear_cache()
    logger.info("通知缓存已清理", extra={"action": "alert.notify"})
