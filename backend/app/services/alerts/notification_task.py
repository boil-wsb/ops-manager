"""
Alert notification service.
"""

import asyncio
import functools
import json
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

_SENSITIVE_KEY_PATTERN = re.compile(
    r"\b(password|passwd|secret|token|api_key|apikey|access_key|private_key|authorization)\b",
    re.IGNORECASE,
)


def _mask_sensitive(data: Any, max_depth: int = 3, _depth: int = 0) -> Any:
    if _depth >= max_depth:
        return "..."
    if isinstance(data, dict):
        return {
            k: ("***" if _SENSITIVE_KEY_PATTERN.search(str(k)) else _mask_sensitive(v, max_depth, _depth + 1))
            for k, v in data.items()
        }
    if isinstance(data, list):
        return [_mask_sensitive(v, max_depth, _depth + 1) for v in data[:5]]
    if isinstance(data, str) and len(data) > 500:
        return data[:500] + "..."
    return data


def _escape_for_json(value: Any) -> Any:
    """递归转义值中的控制字符，使其可安全插入 JSON 字符串。

    模板渲染会将变量值直接插入到 json.dumps 生成的字符串中，
    若值含换行符等控制字符会破坏 JSON 结构，需预先转义。
    """
    if isinstance(value, str):
        # json.dumps 后去掉外层引号，得到转义后的字符串内容
        return json.dumps(value, ensure_ascii=False)[1:-1]
    if isinstance(value, dict):
        return {k: _escape_for_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_escape_for_json(v) for v in value]
    return value


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
            extra={
                "action": "alert.notify",
                "alertname": alert_data.get("alertname"),
                "instance": instance,
            },
        )

    except Exception as exc:
        logger.error(f"处理告警通知失败: {str(exc)}", extra={"action": "alert.notify"})
        raise


# 同批次webhook内resolved批量更新后，firing告警重新下发的抑制窗口（秒）
_RESOLVED_RENOTIFY_BLOCK_SECONDS = 60


async def _check_previous_alert_active(
    db: AsyncSession,
    alertname: str,
    instance: str,
    current_history_id: int | None = None,
) -> bool:
    """检查同alertname+instance的上一个通知记录状态，判断是否应跳过新通知。

    规则：
    - 存在已发送通知的firing记录 → 跳过（告警仍在活跃，不重复下发）
    - 上一个告警刚被恢复（60秒内，可能同批次webhook） → 跳过
    - 上一个告警已恢复超过60秒（真实恢复） → 允许下发
    - 无已发送通知的历史记录 → 允许下发

    注意：不排除当前history_id，因为查询条件已通过 notification_sent=True
    和 feishu_open_message_id IS NOT NULL 过滤掉未通知的新记录/更新记录。

    Returns:
        True: 可以发送通知; False: 应跳过通知
    """
    from sqlalchemy import text as sa_text

    try:
        result = await db.execute(
            sa_text(
                "SELECT id, status, ends_at "
                "FROM alert_history "
                "WHERE alertname = :name "
                "AND labels->>'instance' = :instance "
                "AND notification_sent = True "
                "AND feishu_open_message_id IS NOT NULL "
                "ORDER BY id DESC LIMIT 1"
            ),
            {
                "name": alertname,
                "instance": instance,
            },
        )
        row = result.fetchone()

        if not row:
            return True

        prev_id, prev_status, prev_ends_at = row[0], row[1], row[2]

        if prev_status == "firing":
            logger.info(
                f"上一个告警仍为firing状态，跳过通知: prev_id={prev_id}, "
                f"alertname={alertname}, instance={instance}",
                extra={
                    "action": "alert.notify",
                    "alertname": alertname,
                    "instance": instance,
                    "prev_id": prev_id,
                    "prev_status": prev_status,
                    "skip_reason": "previous_firing",
                },
            )
            return False

        if prev_status == "resolved" and prev_ends_at:
            # 确保时区一致后比较
            prev_ends_dt = prev_ends_at
            if prev_ends_dt.tzinfo is None:
                from app.core.tz import SHANGHAI_TZ

                prev_ends_dt = prev_ends_dt.replace(tzinfo=SHANGHAI_TZ)
            time_since_resolve = (now_shanghai() - prev_ends_dt).total_seconds()
            if time_since_resolve < _RESOLVED_RENOTIFY_BLOCK_SECONDS:
                logger.info(
                    f"上一个告警刚被恢复({time_since_resolve:.0f}秒前，同批次)，"
                    f"跳过通知: prev_id={prev_id}, alertname={alertname}, "
                    f"instance={instance}",
                    extra={
                        "action": "alert.notify",
                        "alertname": alertname,
                        "instance": instance,
                        "prev_id": prev_id,
                        "prev_status": prev_status,
                        "time_since_resolve": time_since_resolve,
                        "skip_reason": "recently_resolved",
                    },
                )
                return False

        return True

    except Exception as exc:
        logger.error(
            f"检查上一个告警状态异常: {str(exc)}",
            extra={"action": "alert.notify", "alertname": alertname, "instance": instance},
        )
        return True


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
    ends_at_raw = alert_data.get("ends_at", "")
    labels = alert_data.get("labels", {})
    annotations = alert_data.get("annotations", {})

    logger.info(f"收到告警数据: {_mask_sensitive(alert_data)}", extra={"action": "alert.notify"})

    starts_at = starts_at_str
    if isinstance(starts_at_str, str):
        try:
            starts_at = datetime.fromisoformat(starts_at_str.replace("Z", "+00:00"))
        except ValueError:
            starts_at = now_shanghai()

    ends_at = None
    if isinstance(ends_at_raw, str) and ends_at_raw:
        try:
            ends_at = datetime.fromisoformat(ends_at_raw.replace("Z", "+00:00"))
        except ValueError:
            ends_at = None
    elif isinstance(ends_at_raw, datetime):
        ends_at = ends_at_raw

    # firing状态下，发送通知前检查上一个同alertname+instance的告警是否已恢复
    if status == "firing":
        can_send = await _check_previous_alert_active(
            db=db,
            alertname=alertname,
            instance=instance,
            current_history_id=alert_data.get("history_id"),
        )
        if not can_send:
            return

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
            ends_at=ends_at,
            labels=labels,
            annotations=annotations,
        )

        if subject and body:
            logger.info(
                f"邮件通知已准备: instance={instance}, subject={subject}",
                extra={"action": "alert.notify", "instance": instance},
            )

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

        alerts_list = alert_data.get("alerts", [])
        external_url = alert_data.get("externalURL", "") or labels.get("externalURL", annotations.get("externalURL", ""))

        subject, body = await alert_template_service.render_alert_template(
            db=db,
            template=feishu_template,
            alertname=alertname,
            status=status,
            severity=severity,
            instance=instance,
            description=description,
            starts_at=starts_at,
            ends_at=ends_at,
            labels=labels,
            annotations=annotations,
            alerts=alerts_list,
            external_url=external_url,
        )

        if body or subject:
            asset_owner_open_id = await _get_asset_owner_open_id(db, instance)

            notification_group_open_ids = await _get_alert_notification_group_open_ids(db)

            recipient_open_ids = []
            if asset_owner_open_id:
                recipient_open_ids.append(asset_owner_open_id)
            for oid in notification_group_open_ids:
                if oid and oid not in recipient_open_ids:
                    recipient_open_ids.append(oid)

            if recipient_open_ids:
                feishu_svc = get_feishu_notification_service()

                card = None
                context = alert_template_service._build_template_context(
                    alertname=alertname,
                    status=status,
                    severity=severity,
                    instance=instance,
                    description=description,
                    starts_at=starts_at,
                    ends_at=ends_at,
                    labels=labels,
                    annotations=annotations,
                    alerts=alerts_list,
                    external_url=external_url,
                )
                context["body"] = body or ""
                context["content"] = body or ""
                context["starts_at"] = context["startsAt"]
                context["ends_at"] = context["endsAt"]

                if feishu_template.card_config:
                    card_config_json = json.dumps(feishu_template.card_config, ensure_ascii=False)
                    rendered_card_str = alert_template_service.render_template(
                        template_str=card_config_json,
                        context=_escape_for_json(context),
                    )
                    logger.info(
                        f"渲染卡片配置: {rendered_card_str[:500]}", extra={"action": "alert.notify"}
                    )
                    try:
                        card = json.loads(rendered_card_str)
                        logger.info("使用模板card_config", extra={"action": "alert.notify"})
                    except json.JSONDecodeError:
                        logger.warning(
                            "card_config渲染后不是有效JSON，将使用body_template构建卡片",
                            extra={"action": "alert.notify"},
                        )
                        card = None

                if not card and body:
                    card_title = subject or f"【{severity.upper()}】{alertname}"
                    card = feishu_svc.build_card_from_markdown(
                        title=card_title,
                        markdown_content=body,
                        severity=severity,
                        status=status,
                        with_actions=(status == "firing"),
                        alertname=alertname,
                        instance=instance,
                    )
                    logger.info("使用body_template构建卡片", extra={"action": "alert.notify"})

                if not card:
                    if status == "resolved":
                        card = feishu_svc.build_resolved_card(
                            alertname=alertname,
                            severity=severity,
                            instance=instance,
                        )
                    else:
                        card = feishu_svc.build_alert_card(
                            alertname=alertname,
                            status=status,
                            severity=severity,
                            instance=instance,
                            description=description,
                            starts_at=context.get("startsAt", ""),
                            env=labels.get("env"),
                        )
                    logger.info(f"使用默认卡片构建: status={status}", extra={"action": "alert.notify"})

                # 根据告警状态动态调整卡片header颜色和body内容
                if isinstance(card, dict) and "header" in card:
                    if status == "resolved":
                        card["header"]["template"] = "green"
                        # 更新状态标签颜色为绿色
                        for tag in card["header"].get("text_tag_list", []):
                            if tag.get("element_id") == "status_tag":
                                tag["color"] = "green"
                    elif status == "firing":
                        severity_color_map = {
                            "critical": "red",
                            "warning": "orange",
                            "info": "blue",
                        }
                        card["header"]["template"] = severity_color_map.get(
                            severity, "red"
                        )

                # resolved状态优化body内容：移除事件详情，增加结束时间和恢复提示，移除操作按钮
                if status == "resolved" and isinstance(card, dict):
                    body = card.get("body", {})
                    elements = body.get("elements", [])

                    # 计算结束时间显示值
                    ends_at_display = ""
                    if ends_at:
                        try:
                            if isinstance(ends_at, str):
                                ends_at_dt = datetime.fromisoformat(
                                    ends_at.replace("Z", "+00:00")
                                )
                            else:
                                ends_at_dt = ends_at
                            ends_at_display = ends_at_dt.strftime("%Y-%m-%d %H:%M:%S")
                        except (ValueError, TypeError):
                            ends_at_display = str(ends_at)[:19]

                    new_elements = []
                    for elem in elements:
                        # 跳过事件详情div，替换为结束时间+恢复提示
                        if (
                            isinstance(elem, dict)
                            and elem.get("tag") == "div"
                            and isinstance(elem.get("text", {}).get("content", ""), str)
                            and "事件详情" in elem["text"]["content"]
                        ):
                            if ends_at_display:
                                new_elements.append(
                                    {
                                        "tag": "div",
                                        "text": {
                                            "tag": "lark_md",
                                            "content": f"🏁 **结束时间**：{ends_at_display}",
                                        },
                                    }
                                )
                            new_elements.append(
                                {
                                    "tag": "div",
                                    "text": {
                                        "tag": "lark_md",
                                        "content": "✅ **该告警已恢复**",
                                    },
                                }
                            )
                            continue
                        new_elements.append(elem)

                    # 移除操作按钮（hr + column_set含button）
                    filtered_elements = []
                    skip_next_hr = False
                    for elem in new_elements:
                        if (
                            isinstance(elem, dict)
                            and elem.get("tag") == "column_set"
                            and any(
                                col.get("tag") == "column"
                                and any(e.get("tag") == "button" for e in col.get("elements", []))
                                for col in elem.get("columns", [])
                            )
                        ):
                            skip_next_hr = True
                            continue
                        if skip_next_hr and elem.get("tag") == "hr":
                            skip_next_hr = False
                            continue
                        skip_next_hr = False
                        filtered_elements.append(elem)

                    body["elements"] = filtered_elements

                # firing状态优化body内容：在事件详情后添加跳转链接
                if status == "firing" and isinstance(card, dict):
                    body = card.get("body", {})
                    elements = body.get("elements", [])

                    # 获取generatorURL
                    generator_url = ""
                    if alerts_list and isinstance(alerts_list, list) and len(alerts_list) > 0:
                        generator_url = alerts_list[0].get("generatorURL", "")

                    link_parts = []
                    if generator_url:
                        link_parts.append(f"[📊 Prometheus图表]({generator_url})")
                    if external_url:
                        link_parts.append(f"[🔔 Alertmanager]({external_url})")

                    if link_parts:
                        link_content = " | ".join(link_parts)
                        new_elements = []
                        for elem in elements:
                            new_elements.append(elem)
                            # 在事件详情div后添加跳转链接
                            if (
                                isinstance(elem, dict)
                                and elem.get("tag") == "div"
                                and isinstance(elem.get("text", {}).get("content", ""), str)
                                and "事件详情" in elem["text"]["content"]
                            ):
                                new_elements.append(
                                    {
                                        "tag": "div",
                                        "text": {
                                            "tag": "lark_md",
                                            "content": f"🔗 **快捷跳转**：{link_content}",
                                        },
                                    }
                                )
                        body["elements"] = new_elements

                logger.info(
                    f"飞书卡片JSON内容: {json.dumps(_mask_sensitive(card), ensure_ascii=False)[:2000]}",
                    extra={"action": "alert.notify"},
                )

                card_updated = False
                if status == "resolved":
                    card_updated = await _update_resolved_alert_card(
                        db=db,
                        alertname=alertname,
                        instance=instance,
                        severity=severity,
                        resolved_card=card,
                    )

                if not card_updated:
                    first_message_id = None
                    for recipient_open_id in recipient_open_ids:
                        result = await asyncio.to_thread(
                            functools.partial(
                                feishu_svc.send_p2p_card_message,
                                open_id=recipient_open_id,
                                card_content=card,
                            )
                        )
                        if result.get("success"):
                            message_id = result.get("message_id")
                            if message_id and first_message_id is None:
                                first_message_id = message_id
                            logger.info(
                                f"P2P飞书卡片已发送: instance={instance}, open_id={recipient_open_id}, status={status}",
                                extra={
                                    "action": "alert.notify",
                                    "instance": instance,
                                    "open_id": recipient_open_id,
                                    "status": status,
                                },
                            )
                        else:
                            logger.warning(
                                f"P2P飞书卡片发送失败: instance={instance}, open_id={recipient_open_id}, status={status}",
                                extra={
                                    "action": "alert.notify",
                                    "instance": instance,
                                    "open_id": recipient_open_id,
                                    "status": status,
                                },
                            )

                    if first_message_id and status == "firing":
                        await _save_firing_alert_message_id(
                            db=db,
                            alertname=alertname,
                            instance=instance,
                            severity=severity,
                            message_id=first_message_id,
                        )

                await _update_alert_history_notification_sent(
                    db=db,
                    alertname=alertname,
                    instance=instance,
                    status=status,
                )
            else:
                logger.info(
                    f"未找到资产负责人或通知组成员: instance={instance}，跳过飞书通知",
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
                extra={
                    "action": "alert.notify",
                    "alertname": alertname,
                    "instance": instance,
                    "history_id": history_id,
                },
            )
        else:
            logger.warning(
                f"未找到firing告警记录: alertname={alertname}, instance={instance}",
                extra={"action": "alert.notify", "alertname": alertname, "instance": instance},
            )

    except Exception as exc:
        logger.error(
            f"保存feishu_open_message_id异常: {str(exc)}", extra={"action": "alert.notify"}
        )


async def _update_resolved_alert_card(
    db: AsyncSession,
    alertname: str,
    instance: str,
    severity: str,
    resolved_card: dict[str, Any] | None = None,
) -> bool:
    """Update the Feishu card for a resolved alert.

    Finds the corresponding firing alert's card and updates it to show 'resolved' status.

    Args:
        db: Database session
        alertname: Alert name
        instance: Instance identifier
        severity: Alert severity
        resolved_card: Pre-rendered resolved card content to use for update

    Returns:
        True if card was successfully updated, False otherwise
    """
    from sqlalchemy import text

    try:
        result = await db.execute(
            text(
                "SELECT id, feishu_open_message_id FROM alert_history WHERE alertname = :name AND labels->>'instance' = :instance AND feishu_open_message_id IS NOT NULL ORDER BY id DESC LIMIT 1"
            ),
            {"name": alertname, "instance": instance},
        )
        row = result.fetchone()

        if not row:
            logger.warning(
                f"未找到firing告警卡片，将发送新的resolved通知: alertname={alertname}, instance={instance}",
                extra={"action": "alert.resolve", "alertname": alertname, "instance": instance},
            )
            return False

        history_id, feishu_open_message_id = row[0], row[1]

        feishu_svc = get_feishu_notification_service()
        card_to_use = resolved_card
        if card_to_use is None:
            card_to_use = feishu_svc.build_resolved_card(
                alertname=alertname,
                severity=severity,
                instance=instance,
            )

        update_result = await asyncio.to_thread(
            functools.partial(
                feishu_svc.update_card_message,
                open_message_id=feishu_open_message_id,
                card_content=card_to_use,
            )
        )

        if update_result.get("success"):
            await db.execute(
                text(
                    "UPDATE alert_history SET status = 'resolved', notification_sent = True WHERE id = :id"
                ),
                {"id": history_id},
            )
            await db.commit()
            logger.info(
                f"卡片已更新为resolved: alertname={alertname}, instance={instance}, history_id={history_id}",
                extra={"action": "alert.resolve", "alertname": alertname, "instance": instance},
            )
            return True
        else:
            logger.error(
                f"更新卡片失败: {update_result.get('error') or update_result.get('message')}",
                extra={"action": "alert.resolve", "alertname": alertname, "instance": instance},
            )
            return False

    except Exception as exc:
        logger.error(
            f"更新resolved告警卡片异常: {str(exc)}",
            extra={"action": "alert.resolve", "alertname": alertname, "instance": instance},
        )
        return False


async def _update_alert_history_notification_sent(
    db: AsyncSession,
    alertname: str,
    instance: str,
    status: str = "firing",
) -> None:
    """Update AlertHistory.notification_sent to True for a specific alert.

    Args:
        db: Database session
        alertname: Alert name
        instance: Instance identifier
        status: Alert status (firing/resolved)
    """
    from sqlalchemy import text

    try:
        result = await db.execute(
            text(
                "SELECT id FROM alert_history WHERE alertname = :name AND labels->>'instance' = :instance AND status = :status ORDER BY id DESC LIMIT 1"
            ),
            {"name": alertname, "instance": instance, "status": status},
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
                f"更新notification_sent=True: id={history_id}, alertname={alertname}, instance={instance}, status={status}",
                extra={"action": "alert.notify", "alertname": alertname, "instance": instance, "status": status},
            )
        else:
            logger.warning(
                f"未找到告警记录(notification_sent): alertname={alertname}, instance={instance}, status={status}",
                extra={"action": "alert.notify", "alertname": alertname, "instance": instance, "status": status},
            )

    except Exception as exc:
        logger.error(
            f"更新notification_sent异常: {str(exc)}",
            extra={"action": "alert.notify", "alertname": alertname, "instance": instance},
        )


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
                    extra={
                        "action": "alert.notify",
                        "instance": instance,
                        "asset_name": asset.name,
                        "username": user.username,
                    },
                )
                return user.feishu_open_id

        logger.debug(
            f"未找到资产负责人: IP={instance}",
            extra={"action": "alert.notify", "instance": instance},
        )
        return None

    except Exception as exc:
        logger.error(
            f"查询资产负责人异常: {instance}: {str(exc)}",
            extra={"action": "alert.notify", "instance": instance},
        )
        return None


NOTIFICATION_TYPE_ALERT_FIRING = "alert_firing"


async def _get_alert_notification_group_open_ids(db: AsyncSession) -> list[str]:
    """Get feishu_open_ids from alert_firing notification group members.

    Args:
        db: Database session

    Returns:
        List of feishu open_ids from the notification group
    """
    try:
        from app.crud.crud_notification_group import notification_group

        groups = await notification_group.get_by_notification_type(
            db, NOTIFICATION_TYPE_ALERT_FIRING
        )
        open_ids = []
        for group in groups:
            if group.is_active:
                for member in group.members:
                    if member.feishu_open_id and member.feishu_open_id not in open_ids:
                        open_ids.append(member.feishu_open_id)
        if open_ids:
            logger.info(
                f"告警通知组成员: {len(open_ids)} 人",
                extra={
                    "action": "alert.notify",
                    "notification_type": NOTIFICATION_TYPE_ALERT_FIRING,
                    "member_count": len(open_ids),
                },
            )
        return open_ids
    except Exception as exc:
        logger.error(f"查询告警通知组异常: {str(exc)}", extra={"action": "alert.notify"})
        return []


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
