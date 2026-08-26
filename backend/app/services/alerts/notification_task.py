"""
Alert notification service.

三阶段分离架构（解决 QueuePool 连接池耗尽问题）:
- prepare_alert_notification(db): 所有 DB 操作 + 释放 session
- execute_feishu_notification(ctx): 飞书调用，不持有 DB session
- save_notification_result(db, ctx, result): 保存 message_id，新 session

历史根因:
- 旧代码 send_alert_notification(data, db) 在飞书调用期间持有 db: AsyncSession
- 飞书 SSL 错误导致 7s 重试，30 个并发请求的 DB session 全部被持有
- → QueuePool size=20 overflow=10 耗尽 → 12,114 次超时错误
"""

import asyncio
import contextlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.tz import now_shanghai, to_shanghai
from app.models.alert import AlertTemplate
from app.models.asset import Asset
from app.models.user import User
from app.services.alerts.alert_inhibition import alert_inhibition_service
from app.services.alerts.alert_template import alert_template_service
from app.services.alerts.feishu_notification import get_feishu_notification_service

logger = get_logger(__name__)


@dataclass
class NotificationContext:
    """阶段 1 输出 / 阶段 2 输入: 飞书发送所需的全部数据.

    设计原则: 包含飞书调用所需的全部信息，不依赖 DB session。
    """

    alertname: str
    instance: str
    status: str  # firing / resolved
    severity: str
    description: str
    starts_at_str: str
    labels: dict[str, Any]
    annotations: dict[str, Any]
    alerts_list: list[dict[str, Any]]
    recipient_open_ids: list[str]
    card: dict[str, Any] | None = None
    # C-05 修复: firing 路径使用的 alert_history.id（由调用方 alerts.py 传入）
    # 用于 _save_firing_alert_card_messages 精确查询，避免依赖 status='firing'
    # 在 firing→resolved 时序交错时返回空导致卡片未保存
    history_id: int | None = None
    # resolved 专用: 待更新的卡片列表（从 alert_card_messages 表查询）
    # 格式: [{"history_id": int, "open_message_id": str, "card_message_id": int}, ...]
    resolved_card_messages: list[dict] = field(default_factory=list)
    # 标记是否需要执行飞书调用
    needs_feishu_send: bool = False
    needs_feishu_update: bool = False


@dataclass
class FeishuResult:
    """阶段 2 输出 / 阶段 3 输入: 飞书调用结果."""

    success: bool = False
    # firing: 所有成功发送的卡片列表 [{"open_message_id": str, "recipient_open_id": str}, ...]
    sent_cards: list[dict] = field(default_factory=list)
    # resolved: 成功更新的 alert_card_messages.id 列表
    updated_card_message_ids: list[int] = field(default_factory=list)
    # resolved: 对应的 alert_history_id（用于更新 alert_history 状态）
    resolved_history_id: int | None = None
    # 标记是否需要执行阶段 3 保存
    needs_save: bool = False


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


# =============================================================================
# 三阶段分离: DB 操作 / 飞书 IO / DB 保存
# 解决 QueuePool 连接池耗尽问题（飞书调用期间不持有 DB session）
# =============================================================================


async def prepare_alert_notification(
    db: AsyncSession,
    alert_data: dict[str, Any],
) -> NotificationContext | None:
    """阶段 1: 完成 DB 操作 + 渲染卡片 + 预占位标记.

    在此函数返回后，调用方应立即释放 DB session，
    然后使用返回的 NotificationContext 执行阶段 2（飞书调用）。

    Returns:
        NotificationContext 或 None（无需发送时返回 None）
    """
    instance = alert_data.get("instance", "")
    alertname = alert_data.get("alertname", "")
    status = alert_data.get("status", "firing")
    severity = alert_data.get("severity", "info")
    description = alert_data.get("description", "")
    starts_at_str_data = alert_data.get("starts_at", "")
    labels = alert_data.get("labels", {})
    annotations = alert_data.get("annotations", {})
    # C-05 修复: 提取调用方 alerts.py 传入的 history_id，避免后续再查询
    history_id_from_caller = alert_data.get("history_id")

    if not instance:
        logger.info("告警无实例信息，跳过通知", extra={"action": "alert.notify"})
        return None

    starts_at = starts_at_str_data
    if isinstance(starts_at_str_data, str):
        try:
            starts_at = datetime.fromisoformat(starts_at_str_data.replace("Z", "+00:00"))
        except ValueError:
            starts_at = now_shanghai()

    starts_at_str = (
        to_shanghai(starts_at).strftime("%Y-%m-%d %H:%M:%S")
        if isinstance(starts_at, datetime)
        else str(starts_at)
    )

    alerts_list = alert_data.get("alerts", [{}])

    # --- DB 查询: 模板 ---
    feishu_templates_result = await db.execute(
        select(AlertTemplate)
        .where(
            AlertTemplate.template_type == "feishu",
            AlertTemplate.is_active.is_(True),
        )
        .order_by(case((AlertTemplate.is_default.is_(True), 0), else_=1))
    )
    feishu_templates = list(feishu_templates_result.scalars().all())

    feishu_template = None
    for template in feishu_templates:
        if template.is_default:
            feishu_template = template
            break
        elif template.is_active and feishu_template is None:
            feishu_template = template

    if not feishu_template:
        logger.info("未找到飞书模板，跳过通知", extra={"action": "alert.notify"})
        # 即使无模板也要标记（防止重复触发）
        # NC-3 修复（第二轮审查）：原调用未传 starts_at，走 else 退化路径
        # （无 starts_at 过滤、无 status 过滤），可能误标记其他周期/其他告警的
        # firing 记录为 notification_sent=True，造成告警永久丢失。补传 starts_at。
        if status != "resolved":
            await _update_alert_history_notification_sent(
                db=db, alertname=alertname, instance=instance, starts_at=starts_at
            )
        return None

    # --- DB 查询: 资产负责人 + 通知组 ---
    asset_owner_open_id = await _get_asset_owner_open_id(db, instance)
    notification_group_open_ids = await _get_alert_notification_group_open_ids(db)

    recipient_open_ids: list[str] = []
    if asset_owner_open_id:
        recipient_open_ids.append(asset_owner_open_id)
    for oid in notification_group_open_ids:
        if oid and oid not in recipient_open_ids:
            recipient_open_ids.append(oid)

    # --- 渲染卡片（纯 CPU，无 DB） ---
    feishu_svc = get_feishu_notification_service()
    card = None

    if feishu_template.card_config:
        external_url = labels.get("externalURL", annotations.get("externalURL", ""))
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
        card_config_json = json.dumps(feishu_template.card_config, ensure_ascii=False)
        rendered_card_str = alert_template_service.render_template(
            template_str=card_config_json,
            context=_escape_for_json(context),
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

    # I-05 修复: 卡片 JSON 截断到 500 字符，避免大卡片占用日志空间
    try:
        card_json = json.dumps(card, ensure_ascii=False, default=str)
        if len(card_json) > 500:
            card_json = card_json[:500] + f"...(truncated, total={len(card_json)})"
        logger.info(f"飞书卡片JSON内容: {card_json}", extra={"action": "alert.notify"})
    except Exception:
        logger.info(f"飞书卡片JSON内容: {card}", extra={"action": "alert.notify"})

    # --- DB 操作: 预占位标记 / resolved 查询 ---
    ctx = NotificationContext(
        alertname=alertname,
        instance=instance,
        status=status,
        severity=severity,
        description=description,
        starts_at_str=starts_at_str,
        labels=labels,
        annotations=annotations,
        alerts_list=alerts_list,
        recipient_open_ids=recipient_open_ids,
        card=card,
        history_id=history_id_from_caller,
    )

    if status == "resolved":
        # resolved: 查询待更新的卡片列表（从 alert_card_messages 表，1:N 关系）
        # 第一性原理：resolved 的目的是更新所有 card_status='firing' 的卡片，
        # 应直接查 alert_card_messages.card_status，而非 alert_history.status。
        # 因为 alerts.py:144-174 的批量更新逻辑会先将 firing 记录的
        # alert_history.status 改为 resolved，若此处仍查 status='firing' 会返回空。
        from sqlalchemy import text as _text

        try:
            # 直接查 alert_card_messages WHERE card_status='firing' JOIN alert_history
            result = await db.execute(
                _text(
                    "SELECT acm.id, acm.open_message_id, acm.alert_history_id "
                    "FROM alert_card_messages acm "
                    "JOIN alert_history ah ON ah.id = acm.alert_history_id "
                    "WHERE ah.alertname = :name AND ah.labels->>'instance' = :instance "
                    "AND acm.card_status = 'firing' "
                    "ORDER BY acm.id DESC"
                ),
                {"name": alertname, "instance": instance},
            )
            card_rows = result.fetchall()
            if not card_rows:
                # 兼容性回退：新表无 firing 卡片时，查旧字段 feishu_open_message_id
                result = await db.execute(
                    _text(
                        "SELECT id, feishu_open_message_id FROM alert_history "
                        "WHERE alertname = :name AND labels->>'instance' = :instance "
                        "AND feishu_open_message_id IS NOT NULL "
                        "ORDER BY id DESC LIMIT 1"
                    ),
                    {"name": alertname, "instance": instance},
                )
                legacy_row = result.fetchone()
                if legacy_row and legacy_row[1]:
                    ctx.resolved_card_messages = [
                        {
                            "history_id": legacy_row[0],
                            "open_message_id": legacy_row[1],
                            "card_message_id": None,
                        }
                    ]
                else:
                    logger.warning(
                        f"未找到待更新卡片: alertname={alertname}, instance={instance}",
                        extra={
                            "action": "alert.resolve",
                            "alertname": alertname,
                            "instance": instance,
                        },
                    )
                    return None
            else:
                ctx.resolved_card_messages = [
                    {
                        "history_id": row[2],
                        "open_message_id": row[1],
                        "card_message_id": row[0],
                    }
                    for row in card_rows
                ]

            history_id = ctx.resolved_card_messages[0]["history_id"]
            ctx.needs_feishu_update = True
            logger.info(
                f"找到待更新卡片: alertname={alertname}, instance={instance}, "
                f"history_id={history_id}, card_count={len(ctx.resolved_card_messages)}",
                extra={
                    "action": "alert.resolve",
                    "alertname": alertname,
                    "instance": instance,
                    "history_id": history_id,
                    "card_count": len(ctx.resolved_card_messages),
                },
            )
        except Exception as exc:
            logger.error(f"查询resolved卡片异常: {str(exc)}", extra={"action": "alert.resolve"})
            return None
    else:
        # firing: 预占位标记
        if recipient_open_ids:
            await _update_alert_history_notification_sent(
                db=db, alertname=alertname, instance=instance, starts_at=starts_at
            )
            ctx.needs_feishu_send = True
        else:
            # 无收件人也要标记（P0-C 修复）
            logger.info(
                f"未找到资产负责人: instance={instance}，跳过飞书通知",
                extra={"action": "alert.notify", "instance": instance},
            )
            await _update_alert_history_notification_sent(
                db=db, alertname=alertname, instance=instance, starts_at=starts_at
            )
            return None

    return ctx


async def execute_feishu_notification(ctx: NotificationContext) -> FeishuResult:
    """阶段 2: 执行飞书调用（不持有 DB session）.

    根据 NotificationContext 执行:
    - firing: send_p2p_card_message（通过 asyncio.to_thread）
    - resolved: update_card_message（通过 asyncio.to_thread）

    Returns:
        FeishuResult: 飞书调用结果，供阶段 3 保存
    """
    feishu_svc = get_feishu_notification_service()
    result = FeishuResult()

    if ctx.needs_feishu_send and ctx.card and ctx.recipient_open_ids:
        sent_cards: list[dict] = []
        for recipient_open_id in ctx.recipient_open_ids:
            try:
                send_result = await asyncio.to_thread(
                    feishu_svc.send_p2p_card_message,
                    open_id=recipient_open_id,
                    card_content=ctx.card,
                )
                if send_result.get("success"):
                    message_id = send_result.get("message_id")
                    if message_id:
                        sent_cards.append(
                            {
                                "open_message_id": message_id,
                                "recipient_open_id": recipient_open_id,
                            }
                        )
                    logger.info(
                        f"P2P飞书卡片已发送: instance={ctx.instance}, open_id={recipient_open_id}",
                        extra={
                            "action": "alert.notify",
                            "instance": ctx.instance,
                            "open_id": recipient_open_id,
                        },
                    )
                else:
                    logger.warning(
                        f"P2P飞书卡片发送失败: instance={ctx.instance}, open_id={recipient_open_id}",
                        extra={
                            "action": "alert.notify",
                            "instance": ctx.instance,
                            "open_id": recipient_open_id,
                        },
                    )
            except Exception as exc:
                logger.error(
                    f"P2P飞书卡片发送异常: instance={ctx.instance}, open_id={recipient_open_id}, error={exc}",
                    extra={
                        "action": "alert.notify",
                        "instance": ctx.instance,
                        "open_id": recipient_open_id,
                    },
                )
        result.sent_cards = sent_cards
        result.success = len(sent_cards) > 0
        result.needs_save = len(sent_cards) > 0

    elif ctx.needs_feishu_update and ctx.resolved_card_messages:
        try:
            resolved_card = feishu_svc.build_resolved_card(
                alertname=ctx.alertname,
                severity=ctx.severity,
                instance=ctx.instance,
            )
            updated_card_message_ids: list[int] = []
            for card_msg in ctx.resolved_card_messages:
                try:
                    update_result = await asyncio.to_thread(
                        feishu_svc.update_card_message,
                        open_message_id=card_msg["open_message_id"],
                        card_content=resolved_card,
                    )
                    if update_result.get("success"):
                        updated_card_message_ids.append(card_msg["card_message_id"])
                        logger.info(
                            f"卡片已更新为resolved: alertname={ctx.alertname}, instance={ctx.instance}, message_id={card_msg['open_message_id']}",
                            extra={
                                "action": "alert.resolve",
                                "alertname": ctx.alertname,
                                "instance": ctx.instance,
                            },
                        )
                    else:
                        logger.error(
                            f"更新卡片失败: message_id={card_msg['open_message_id']}, error={update_result.get('message')}",
                            extra={"action": "alert.resolve"},
                        )
                except Exception as exc:
                    logger.error(
                        f"更新卡片异常: message_id={card_msg['open_message_id']}, error={exc}",
                        extra={"action": "alert.resolve"},
                    )
            result.updated_card_message_ids = updated_card_message_ids
            result.resolved_history_id = ctx.resolved_card_messages[0]["history_id"]
            result.success = len(updated_card_message_ids) > 0
            result.needs_save = len(updated_card_message_ids) > 0
        except Exception as exc:
            logger.error(f"更新resolved告警卡片异常: {str(exc)}", extra={"action": "alert.resolve"})

    return result


async def save_notification_result(
    db: AsyncSession,
    ctx: NotificationContext,
    result: FeishuResult,
) -> None:
    """阶段 3: 保存飞书调用结果到 DB（使用新 session）.

    - firing: 批量 INSERT alert_card_messages
    - resolved: UPDATE alert_card_messages.card_status + alert_history.status

    C-01 修复: 若 firing 路径所有收件人发送失败（sent_cards 为空），
    回滚预占位的 notification_sent=True，让 Alertmanager 重发时去重检查
    不通过从而重新触发通知，避免告警永久丢失。
    回滚必须在阶段 3（持有 DB session）执行，不能在阶段 2（execute_feishu_notification
    不持有 DB session）内执行，否则违反三阶段分离架构核心不变式。
    """
    # C-01: firing 全部失败时回滚预占位标记
    if ctx.status != "resolved" and ctx.needs_feishu_send and not result.sent_cards:
        from sqlalchemy import text as _text

        try:
            if ctx.history_id is not None:
                await db.execute(
                    _text("UPDATE alert_history SET notification_sent = false WHERE id = :id"),
                    {"id": ctx.history_id},
                )
                await db.commit()
                logger.error(
                    f"All recipients failed, rolled back notification_sent: "
                    f"history_id={ctx.history_id}, alertname={ctx.alertname}, "
                    f"instance={ctx.instance}",
                    extra={
                        "action": "alert.notify",
                        "alertname": ctx.alertname,
                        "instance": ctx.instance,
                        "history_id": ctx.history_id,
                    },
                )
            else:
                logger.error(
                    f"All recipients failed but history_id is None, cannot rollback: "
                    f"alertname={ctx.alertname}, instance={ctx.instance}",
                    extra={
                        "action": "alert.notify",
                        "alertname": ctx.alertname,
                        "instance": ctx.instance,
                    },
                )
        except Exception as exc:
            with contextlib.suppress(Exception):
                await db.rollback()
            logger.error(
                f"Failed to rollback notification_sent (DB error): "
                f"history_id={ctx.history_id}, error={exc}",
                extra={
                    "action": "alert.notify",
                    "history_id": ctx.history_id,
                    "error": str(exc),
                },
            )
        return

    if not result.needs_save:
        return

    if ctx.status != "resolved" and result.sent_cards:
        await _save_firing_alert_card_messages(
            db=db,
            alertname=ctx.alertname,
            instance=ctx.instance,
            sent_cards=result.sent_cards,
            history_id=ctx.history_id,
        )
    elif ctx.status == "resolved" and result.updated_card_message_ids:
        from sqlalchemy import text as _text

        try:
            # 1. 更新 alert_card_messages.card_status = 'resolved'
            for cm_id in result.updated_card_message_ids:
                if cm_id is not None:
                    await db.execute(
                        _text(
                            "UPDATE alert_card_messages SET card_status = 'resolved' WHERE id = :id"
                        ),
                        {"id": cm_id},
                    )

            # I-02 修复: 仅当所有卡片都更新成功时才改 alert_history.status = 'resolved'
            # 部分失败时保持 firing 状态，让 Alertmanager 下次重发 resolved webhook 时重试
            # 未成功的卡片（避免告警状态提前关闭但卡片仍停留 firing 的不一致）
            total_cards = len(ctx.resolved_card_messages)
            updated_cards = len(result.updated_card_message_ids)
            all_updated = total_cards > 0 and updated_cards == total_cards

            if all_updated:
                # 2. 所有卡片都更新成功，更新 alert_history.status = 'resolved'
                if result.resolved_history_id:
                    await db.execute(
                        _text(
                            "UPDATE alert_history SET status = 'resolved', notification_sent = True "
                            "WHERE id = :id"
                        ),
                        {"id": result.resolved_history_id},
                    )
                await db.commit()
                logger.info(
                    f"resolved状态已保存(DB): alertname={ctx.alertname}, instance={ctx.instance}, "
                    f"updated_cards={updated_cards}/{total_cards}",
                    extra={
                        "action": "alert.resolve",
                        "alertname": ctx.alertname,
                        "instance": ctx.instance,
                        "updated_cards": updated_cards,
                        "total_cards": total_cards,
                    },
                )
            else:
                # 部分卡片更新失败：保持 alert_history.status = 'firing'，
                # 仅 commit 已更新的 card_status，记录失败卡片供下次 webhook 重试
                await db.commit()
                failed_card_ids = [
                    cm["card_message_id"]
                    for cm in ctx.resolved_card_messages
                    if cm["card_message_id"] not in result.updated_card_message_ids
                ]
                logger.error(
                    f"Partial card update failure, keeping alert_history.status='firing': "
                    f"alertname={ctx.alertname}, instance={ctx.instance}, "
                    f"updated={updated_cards}/{total_cards}, "
                    f"failed_card_message_ids={failed_card_ids}",
                    extra={
                        "action": "alert.resolve",
                        "alertname": ctx.alertname,
                        "instance": ctx.instance,
                        "updated_cards": updated_cards,
                        "total_cards": total_cards,
                        "failed_card_message_ids": failed_card_ids,
                    },
                )
        except Exception as exc:
            with contextlib.suppress(Exception):
                await db.rollback()
            logger.error(f"保存resolved状态异常: {str(exc)}", extra={"action": "alert.resolve"})


async def _save_firing_alert_card_messages(
    db: AsyncSession,
    alertname: str,
    instance: str,
    sent_cards: list[dict],
    history_id: int | None = None,
) -> None:
    """批量保存 firing 阶段发送的卡片记录到 alert_card_messages 表.

    C-05 修复: 优先使用调用方传入的 history_id 精确查询（主键），
    避免查询 status='firing' 在 firing→resolved 时序交错时返回空导致卡片未保存。
    """
    from sqlalchemy import text as _text

    try:
        # C-05 修复: 优先用主键精确查询，避免依赖 status='firing'
        if history_id is not None:
            history_id_to_use = history_id
        else:
            # 向后兼容: 无 history_id 时退化为旧查询（不应触发，调用方 alerts.py 必传）
            result = await db.execute(
                _text(
                    "SELECT id FROM alert_history "
                    "WHERE alertname = :name AND labels->>'instance' = :instance "
                    "AND status = 'firing' ORDER BY id DESC LIMIT 1"
                ),
                {"name": alertname, "instance": instance},
            )
            row = result.fetchone()
            if not row:
                logger.warning(
                    f"未找到firing记录: alertname={alertname}, instance={instance}",
                    extra={"action": "alert.notify", "alertname": alertname, "instance": instance},
                )
                return
            history_id_to_use = row[0]

        for card in sent_cards:
            await db.execute(
                _text(
                    # C-06 修复: ON CONFLICT 处理重试场景
                    # 若同一 (alert_history_id, recipient_open_id) 已存在（重试场景），
                    # 更新 message_id 和 card_status='firing'，不抛 IntegrityError
                    "INSERT INTO alert_card_messages "
                    "(alert_history_id, open_message_id, recipient_open_id, card_status) "
                    "VALUES (:hid, :mid, :oid, 'firing') "
                    "ON CONFLICT (alert_history_id, recipient_open_id) DO UPDATE SET "
                    "open_message_id = EXCLUDED.open_message_id, "
                    "card_status = 'firing'"
                ),
                {
                    "hid": history_id_to_use,
                    "mid": card["open_message_id"],
                    "oid": card["recipient_open_id"],
                },
            )
        await db.commit()
        logger.info(
            f"批量保存卡片记录: alertname={alertname}, instance={instance}, "
            f"history_id={history_id_to_use}, card_count={len(sent_cards)}",
            extra={
                "action": "alert.notify",
                "alertname": alertname,
                "instance": instance,
                "history_id": history_id_to_use,
            },
        )
    except Exception as exc:
        with contextlib.suppress(Exception):
            await db.rollback()
        logger.error(f"批量保存卡片记录异常: {str(exc)}", extra={"action": "alert.notify"})


async def _update_alert_history_notification_sent(
    db: AsyncSession,
    alertname: str,
    instance: str,
    starts_at: datetime | None = None,
) -> None:
    """Update AlertHistory.notification_sent to True for a specific alert.

    Args:
        db: Database session
        alertname: Alert name
        instance: Instance identifier
        starts_at: 告警开始时间（C-02 修复: 精确匹配当前周期，避免误标记旧记录）
    """
    from sqlalchemy import text

    try:
        # C-02 修复: 加 starts_at 过滤 + ORDER BY id DESC LIMIT 1
        # 原问题: 同 alertname+instance 多条 firing 记录时 fetchone() 返回任意行
        # 修复后: 仅匹配当前 starts_at 周期的最新一条
        if starts_at is not None:
            result = await db.execute(
                text(
                    "SELECT id FROM alert_history "
                    "WHERE alertname = :name AND labels->>'instance' = :instance "
                    "AND status = 'firing' AND starts_at = :starts_at "
                    "ORDER BY id DESC LIMIT 1"
                ),
                {"name": alertname, "instance": instance, "starts_at": starts_at},
            )
        else:
            # 向后兼容: 无 starts_at 时仅加 ORDER BY（不应触发，调用方必传）
            result = await db.execute(
                text(
                    "SELECT id FROM alert_history "
                    "WHERE alertname = :name AND labels->>'instance' = :instance "
                    "AND status = 'firing' "
                    "ORDER BY id DESC LIMIT 1"
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
        # 回滚失效事务，避免后续查询全部命中 PendingRollbackError
        with contextlib.suppress(Exception):
            await db.rollback()
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
