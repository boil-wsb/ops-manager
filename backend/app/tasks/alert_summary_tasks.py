"""每日告警汇总定时任务

每日 09:05 汇总上一日的未解决告警并发送飞书通知。

口径（2026-10-08 与需求方确认）：
- 未解决 = 截至昨日末仍处于 firing 的告警（含更早开始的遗留告警），
  以及昨日末仍 firing、今日才恢复的告警（标注恢复时间）
- 排除静默告警（is_suppressed=True）
- 按 alertname+instance 去重合并，统计昨日触发次数
- 通知目标：飞书群聊（system_config: alert_summary.chat_id）
  + alert_firing 通知组成员 P2P，两者都发
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import and_, select

from app.config import settings
from app.core.logging import get_logger
from app.core.tz import now_shanghai
from app.db.session import db_operation_with_retry

logger = get_logger(__name__)

SEVERITY_ORDER = {"critical": 0, "warning": 1, "info": 2}
CARD_MAX_ITEMS = 50  # 卡片最多展示的合并条数，防止消息超长
DESC_MAX_LEN = 200  # 卡片中单条描述截断长度

SUMMARY_CHAT_ID_CONFIG_KEY = "alert_summary.chat_id"
FIRING_GROUP_TYPE = "alert_firing"


def yesterday_window(now: datetime) -> tuple[datetime, datetime]:
    """返回上一自然日窗口 [yesterday_start, today_start)。"""
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return today_start - timedelta(days=1), today_start


def merge_alert_records(
    records: list[Any], window_start: datetime, window_end: datetime
) -> list[dict[str, Any]]:
    """按 alertname+instance 去重合并告警记录。

    - severity 取组内最高（critical > warning > 其他）
    - fire_count 为昨日窗口内不同 starts_at 的触发次数
    - first_starts_at 取组内最早触发时间（可为窗口前的老告警）
    - description 取组内最新记录（id 最大）
    - resolved_at 非空表示整组今日才恢复（昨日末仍未解决），取最大 ends_at
    - 若组内存在 firing 记录，整组视为仍未解决
    """
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for rec in sorted(records, key=lambda r: r.id):
        labels = rec.labels or {}
        instance = labels.get("instance", "")
        key = (rec.alertname, instance)
        group = grouped.get(key)
        if group is None:
            group = {
                "alertname": rec.alertname,
                "instance": instance,
                "severity": rec.severity,
                "fire_count": 0,
                "first_starts_at": rec.starts_at,
                "description": "",
                "resolved_at": None,
                "has_firing": False,
            }
            grouped[key] = group

        if window_start <= rec.starts_at < window_end:
            group["fire_count"] += 1

        if rec.starts_at < group["first_starts_at"]:
            group["first_starts_at"] = rec.starts_at

        if SEVERITY_ORDER.get(rec.severity, 99) < SEVERITY_ORDER.get(group["severity"], 99):
            group["severity"] = rec.severity

        group["description"] = (rec.annotations or {}).get("description", "")

        if rec.status == "firing":
            group["has_firing"] = True
        elif rec.status == "resolved" and rec.ends_at:
            if group["resolved_at"] is None or rec.ends_at > group["resolved_at"]:
                group["resolved_at"] = rec.ends_at

    merged = list(grouped.values())
    for group in merged:
        if group["has_firing"]:
            group["resolved_at"] = None

    merged.sort(
        key=lambda g: (
            SEVERITY_ORDER.get(g["severity"], 99),
            g["first_starts_at"],
        )
    )
    return merged


def build_summary_markdown(
    merged: list[dict[str, Any]], window_start: datetime, window_end: datetime
) -> str:
    """构建汇总卡片 markdown 正文。"""
    if not merged:
        return f"上一日（{window_start:%m-%d}）无未解决告警，一切正常。"

    sections: dict[str, list[str]] = {"critical": [], "warning": [], "info": []}
    for idx, group in enumerate(merged[:CARD_MAX_ITEMS], start=1):
        if group["resolved_at"]:
            state = f"今日 {group['resolved_at']:%H:%M} 已恢复"
        else:
            state = "**仍未解决**"
        line = f"{idx}. **{group['alertname']}** @ {group['instance'] or 'N/A'} — {state}"
        if group["fire_count"] > 0:
            line += f"，昨日触发 {group['fire_count']} 次"
        line += f"，首触 {group['first_starts_at']:%m-%d %H:%M}"
        desc = (group.get("description") or "").strip()
        if desc:
            if len(desc) > DESC_MAX_LEN:
                desc = desc[:DESC_MAX_LEN] + "..."
            line += f"\n   > {desc}"
        sections.setdefault(group["severity"], []).append(line)

    labels = {"critical": "严重", "warning": "警告", "info": "提示"}
    parts: list[str] = []
    for severity in ("critical", "warning", "info"):
        items = sections.get(severity, [])
        if items:
            parts.append(f"**{labels[severity]}（{severity}）— {len(items)} 条**")
            parts.extend(items)

    if len(merged) > CARD_MAX_ITEMS:
        parts.append(f"\n（其余 {len(merged) - CARD_MAX_ITEMS} 条已省略，请到系统查看完整告警历史）")
    return "\n".join(parts)


async def _prepare_summary(db) -> dict[str, Any]:
    """阶段 1（DB session 内）：查询、合并、构建卡片与收件人。"""
    from app.crud.crud_notification_group import notification_group as crud_notification_group
    from app.crud.crud_system_config import crud_system_config
    from app.models.alert import AlertHistory, AlertHistoryStatus
    from app.services.alerts.feishu_notification import get_feishu_notification_service

    window_start, window_end = yesterday_window(now_shanghai())

    still_firing = select(AlertHistory).where(
        and_(
            AlertHistory.status == AlertHistoryStatus.FIRING.value,
            AlertHistory.is_suppressed.is_(False),
            AlertHistory.starts_at < window_end,
        )
    )
    resolved_late = select(AlertHistory).where(
        and_(
            AlertHistory.status == AlertHistoryStatus.RESOLVED.value,
            AlertHistory.is_suppressed.is_(False),
            AlertHistory.starts_at < window_end,
            # 今日才恢复 = 昨日末仍未解决
            AlertHistory.ends_at >= window_end,
        )
    )

    firing_rows = (await db.execute(still_firing)).scalars().all()
    resolved_rows = (await db.execute(resolved_late)).scalars().all()
    merged = merge_alert_records(list(firing_rows) + list(resolved_rows), window_start, window_end)

    feishu_svc = get_feishu_notification_service()
    has_critical = any(g["severity"] == "critical" for g in merged)
    has_warning = any(g["severity"] == "warning" for g in merged)
    if not merged:
        header_severity, header_status = "info", "resolved"  # 绿色：一切正常
    elif has_critical:
        header_severity, header_status = "critical", "firing"  # 红色
    elif has_warning:
        header_severity, header_status = "warning", "firing"  # 橙色
    else:
        header_severity, header_status = "info", "firing"  # 蓝色

    title = f"【告警汇总】{window_start:%m-%d} 未解决告警 {len(merged)} 条"
    markdown = build_summary_markdown(merged, window_start, window_end)
    card = feishu_svc.build_card_from_markdown(
        title=title,
        markdown_content=markdown,
        severity=header_severity,
        status=header_status,
        with_actions=False,
    )

    # 收件人：群聊 chat_id + alert_firing 通知组成员
    chat_id = await crud_system_config.get_value(db, SUMMARY_CHAT_ID_CONFIG_KEY)
    if chat_id is None:
        chat_id = settings.alert_summary_chat_id

    recipient_open_ids: list[str] = []
    groups = await crud_notification_group.get_by_notification_type(db, FIRING_GROUP_TYPE)
    for group in groups:
        for user in group.members:
            if user.feishu_open_id and user.feishu_open_id not in recipient_open_ids:
                recipient_open_ids.append(user.feishu_open_id)

    logger.info(
        f"告警汇总数据构建完成: total={len(merged)}, chat_id={'configured' if chat_id else 'empty'}, "
        f"recipients={len(recipient_open_ids)}",
        extra={
            "action": "alert.summary",
            "total": len(merged),
            "window_start": window_start.isoformat(),
            "window_end": window_end.isoformat(),
            "recipients": len(recipient_open_ids),
            "chat_configured": bool(chat_id),
        },
    )

    return {
        "total": len(merged),
        "card": card,
        "chat_id": chat_id or "",
        "recipient_open_ids": recipient_open_ids,
    }


async def _send_summary(summary: dict[str, Any]) -> dict[str, Any]:
    """阶段 2（不持有 DB session）：执行飞书发送。"""
    from app.integrations.feishu.service import get_feishu_service
    from app.services.alerts.feishu_notification import get_feishu_notification_service

    card = summary["card"]
    chat_id = summary["chat_id"]
    recipient_open_ids = summary["recipient_open_ids"]

    chat_ok = False
    if chat_id:
        try:
            await asyncio.to_thread(
                get_feishu_service().send_message_to_user,
                user_id=chat_id,
                msg_type="interactive",
                content=card,
                receive_id_type="chat_id",
            )
            chat_ok = True
        except Exception as exc:
            logger.error(
                f"告警汇总群聊发送失败: chat_id={chat_id}, error={exc}",
                extra={"action": "alert.summary", "chat_id": chat_id, "error": str(exc)},
            )
    else:
        logger.warning(
            "告警汇总群聊 chat_id 未配置，跳过群发",
            extra={"action": "alert.summary", "config_key": SUMMARY_CHAT_ID_CONFIG_KEY},
        )

    feishu_svc = get_feishu_notification_service()
    sent_p2p, failed_p2p = 0, 0
    for open_id in recipient_open_ids:
        try:
            result = await asyncio.to_thread(
                feishu_svc.send_p2p_card_message,
                open_id=open_id,
                card_content=card,
            )
            if result.get("success"):
                sent_p2p += 1
            else:
                failed_p2p += 1
        except Exception as exc:
            failed_p2p += 1
            logger.error(
                f"告警汇总 P2P 发送异常: open_id={open_id}, error={exc}",
                extra={"action": "alert.summary", "open_id": open_id, "error": str(exc)},
            )

    logger.info(
        f"告警汇总发送完成: total={summary['total']}, chat_ok={chat_ok}, "
        f"p2p_sent={sent_p2p}, p2p_failed={failed_p2p}",
        extra={
            "action": "alert.summary",
            "total": summary["total"],
            "chat_ok": chat_ok,
            "p2p_sent": sent_p2p,
            "p2p_failed": failed_p2p,
        },
    )
    return {"chat_ok": chat_ok, "p2p_sent": sent_p2p, "p2p_failed": failed_p2p}


async def daily_alert_summary_task() -> dict[str, Any]:
    """每日 09:05 汇总上一日未解决告警并发送飞书通知（群聊 + 通知组 P2P）。"""
    logger.info("开始每日告警汇总", extra={"action": "alert.summary"})
    try:
        summary = await db_operation_with_retry(_prepare_summary, max_retries=3, retry_delay=2.0)
        send_result = await _send_summary(summary)
        result_summary = (
            f"昨日未解决告警 {summary['total']} 条, "
            f"群聊{'成功' if send_result['chat_ok'] else '未发送/失败'}, "
            f"P2P 成功 {send_result['p2p_sent']} / 失败 {send_result['p2p_failed']}"
        )
        return {
            "status": "success",
            "result_summary": result_summary,
            "total": summary["total"],
        }
    except Exception as exc:
        logger.error(
            f"每日告警汇总任务失败: {exc}",
            extra={"action": "alert.summary", "error": str(exc)},
        )
        return {"status": "failed", "error": str(exc)}
