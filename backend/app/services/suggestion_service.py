"""
Suggestion service: card building, notification sending, and business helpers.

Shared by the suggestions API and the Feishu callback handler.
"""

import asyncio
import secrets
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.tz import now_shanghai
from app.crud.crud_notification_group import notification_group
from app.models.suggestion import Suggestion, SuggestionStatus

logger = get_logger(__name__)

NOTIFICATION_TYPE_SUGGESTION_MARKET_REVIEW = "suggestion_market_review"

# 6位查询码字符集：去除易混淆字符 I/O/0/1
_QUERY_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


async def generate_query_code(db: AsyncSession) -> str:
    """Generate a unique 6-char query code (collision-checked).

    I-06 修复：
    1. fallback 路径也进入查重循环，避免返回未查重的 code。
    2. SELECT 查重存在 TOCTOU 竞态（两个并发调用可能同时 SELECT 返回 None），
       调用方必须在 INSERT 时捕获 IntegrityError（query_code unique 约束）并重试。

    NC-2 修复（第二轮审查）：
    原先 fallback 生成 8 字符 code，但 DB 列为 VARCHAR(6)，会触发 DataError
    （非 IntegrityError 子类，调用方 except IntegrityError 无法捕获，直接 500）。
    现改为 fallback 仍使用 6 字符 + 增加循环次数（20→30→50），不依赖放宽长度。
    理论容量 32^6 ≈ 10 亿，50 次循环耗尽的概率接近 0。
    """
    # 先尝试 6-char code（30 次）
    for _ in range(30):
        code = "".join(secrets.choice(_QUERY_CODE_ALPHABET) for _ in range(6))
        exists = (
            await db.execute(select(Suggestion.id).where(Suggestion.query_code == code))
        ).scalar_one_or_none()
        if not exists:
            return code
    # 30 次全部冲突（极小概率），再试 50 次（仍为 6 字符）
    logger.warning(
        "6-char query code exhausted after 30 attempts, retrying with 50 more attempts (still 6-char)",
        extra={"action": "suggestion.generate_code", "retry_round": 2},
    )
    for _ in range(50):
        code = "".join(secrets.choice(_QUERY_CODE_ALPHABET) for _ in range(6))
        exists = (
            await db.execute(select(Suggestion.id).where(Suggestion.query_code == code))
        ).scalar_one_or_none()
        if not exists:
            return code
    # 理论上不会到达，抛异常让调用方处理
    raise RuntimeError("Failed to generate unique query code after 80 attempts")


def get_client_ip(request: Any) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    if request.client:
        return request.client.host
    return "unknown"


async def get_market_reviewer_open_ids(db: AsyncSession) -> list[str]:
    """Get feishu open_ids of market review notification group members."""
    groups = await notification_group.get_by_notification_type(
        db, NOTIFICATION_TYPE_SUGGESTION_MARKET_REVIEW
    )
    open_ids: list[str] = []
    for group in groups:
        ids = await notification_group.get_group_member_feishu_ids(db, group.id)
        open_ids.extend(ids)
    return list(set(open_ids))


def _truncate(text: str | None, length: int = 200) -> str:
    if not text:
        return "无"
    return text if len(text) <= length else text[:length] + "..."


def _build_tags_rows(tags: list[dict[str, str]]) -> list[dict]:
    """Build column_set elements from label/value pairs."""
    icon_map = {
        "意见内容": "💬",
        "项目亮点": "⭐",
        "创新Idea": "💡",
        "指派部门": "🏷️",
        "指派人": "👤",
        "提交时间": "⏱️",
        "审批人": "✅",
        "审批时间": "🕐",
        "驳回原因": "❌",
        "执行结果": "📋",
        "存档时间": "📦",
    }
    elements = []
    for tag in tags:
        label = tag.get("label", "")
        value = tag.get("value", "")
        icon = icon_map.get(label, "")
        elements.append(
            {
                "tag": "column_set",
                "flex_mode": "flow",
                "columns": [
                    {
                        "tag": "column",
                        "width": "auto",
                        "elements": [
                            {
                                "tag": "div",
                                "text": {"tag": "lark_md", "content": f"**{icon} {label}**"},
                            }
                        ],
                    },
                    {
                        "tag": "column",
                        "width": "auto",
                        "elements": [
                            {"tag": "div", "text": {"tag": "lark_md", "content": value}}
                        ],
                    },
                ],
            }
        )
    return elements


def _build_card(
    title: str,
    tags: list[dict[str, str]] | None = None,
    body_elements: list[dict] | None = None,
    header_template: str = "orange",
) -> dict[str, Any]:
    """Build a Feishu interactive card content dict (schema 2.0)."""
    elements: list[dict] = []
    if tags:
        elements.extend(_build_tags_rows(tags))
    if body_elements:
        elements.extend(body_elements)
    return {
        "schema": "2.0",
        "header": {
            "title": {"tag": "plain_text", "content": title},
            "template": header_template,
        },
        "body": {"elements": elements},
    }


def _get_feishu_service():
    from app.integrations.feishu.service import get_feishu_service

    return get_feishu_service()


# ---------------- Card senders (sync core + async thin wrapper) ----------------
# I-09 修复：同步版本是核心实现（直接调用飞书 service 同步 API），
# async 版本是薄包装（通过 asyncio.to_thread 调用同步版本）。
# 飞书回调线程直接调用同步版本，避免 asyncio.run() 创建/销毁事件循环。


def _send_with_retry(
    send_func: Any,
    suggestion_id: int,
    open_id: str,
    card: dict[str, Any],
    max_retries: int = 3,
) -> str | None:
    """I-07 修复：飞书卡片发送 3 次指数退避重试（1s→2s→4s）。

    Args:
        send_func: 同步发送函数，签名 (open_id, msg_type, card, id_type) -> dict
        suggestion_id: 建议 ID（用于日志）
        open_id: 收件人 open_id
        card: 卡片内容
        max_retries: 最大重试次数

    Returns:
        message_id 或 None（全部失败）
    """
    import time

    for attempt in range(1, max_retries + 1):
        try:
            result = send_func(open_id, "interactive", card, "open_id")
            msg_id = result.get("message_id") if isinstance(result, dict) else None
            if attempt > 1:
                logger.info(
                    f"Suggestion card send succeeded on retry {attempt}/{max_retries}: "
                    f"suggestion={suggestion_id}, open_id={open_id}, msg_id={msg_id}",
                    extra={
                        "action": "suggestion.notify",
                        "suggestion_id": suggestion_id,
                        "message_id": msg_id,
                        "retry_attempt": attempt,
                        "retry_succeeded": True,
                    },
                )
            return msg_id
        except Exception as e:
            if attempt < max_retries:
                delay = 2 ** (attempt - 1)  # 1s, 2s, 4s
                logger.warning(
                    f"Suggestion card send failed (attempt {attempt}/{max_retries}), "
                    f"retrying in {delay}s: suggestion={suggestion_id}, open_id={open_id}, err={e}",
                    extra={
                        "action": "suggestion.notify",
                        "suggestion_id": suggestion_id,
                        "retry_attempt": attempt,
                        "retry_delay": delay,
                        "error": str(e),
                    },
                )
                time.sleep(delay)
            else:
                logger.error(
                    f"Suggestion card send failed after {max_retries} attempts: "
                    f"suggestion={suggestion_id}, open_id={open_id}, err={e}",
                    extra={
                        "action": "suggestion.notify",
                        "suggestion_id": suggestion_id,
                        "retry_attempt": attempt,
                        "retry_exhausted": True,
                        "error": str(e),
                    },
                )
    # I-07: 全部失败返回 None，调用方通过 None 区分"未发送"和"发送失败"
    # 可结合 notification_status='failed' 字段标记（如需新增字段，在此扩展）
    return None


def _update_card_with_retry(
    open_message_id: str,
    card: dict[str, Any],
    action: str = "suggestion.update",
    max_retries: int = 3,
) -> bool:
    """ND-3 修复（第二轮审查）：飞书卡片更新 3 次指数退避重试（1s→2s→4s）。

    与 _send_with_retry 对称，包装 update_card_message 调用。
    update_card_message 内部 catch 异常返回 {"success": False} 不抛异常，
    此函数主动检查返回值并重试。

    Args:
        open_message_id: 飞书消息 ID
        card: 卡片内容
        action: 日志 action 字段
        max_retries: 最大重试次数

    Returns:
        True 成功 / False 全部失败
    """
    import time

    feishu = _get_feishu_service()
    for attempt in range(1, max_retries + 1):
        try:
            result = feishu.update_card_message(open_message_id, card)
            # update_card_message 返回 dict，检查 success 字段
            if isinstance(result, dict) and result.get("success", True):
                if attempt > 1:
                    logger.info(
                        f"Card update succeeded on retry {attempt}/{max_retries}: "
                        f"message_id={open_message_id}",
                        extra={
                            "action": action,
                            "message_id": open_message_id,
                            "retry_attempt": attempt,
                            "retry_succeeded": True,
                        },
                    )
                return True
            # success=False，视为失败进入重试
            raise RuntimeError(f"update_card_message returned success=False: {result}")
        except Exception as e:
            if attempt < max_retries:
                delay = 2 ** (attempt - 1)  # 1s, 2s, 4s
                logger.warning(
                    f"Card update failed (attempt {attempt}/{max_retries}), "
                    f"retrying in {delay}s: message_id={open_message_id}, err={e}",
                    extra={
                        "action": action,
                        "message_id": open_message_id,
                        "retry_attempt": attempt,
                        "retry_delay": delay,
                        "error": str(e),
                    },
                )
                time.sleep(delay)
            else:
                logger.error(
                    f"Card update failed after {max_retries} attempts: "
                    f"message_id={open_message_id}, err={e}",
                    extra={
                        "action": action,
                        "message_id": open_message_id,
                        "retry_attempt": attempt,
                        "retry_exhausted": True,
                        "error": str(e),
                    },
                )
    return False


def send_pending_card_sync(
    open_id: str,
    suggestion_id: int,
    assignment_id: int,
    content: str,
    highlights: str | None,
    innovation_ideas: str | None,
    dept_names: str,
) -> str | None:
    """Send the pending-approval card to a dept leader / assignee. Returns open_message_id.

    I-07 修复：3 次指数退避重试（1s→2s→4s），全部失败返回 None。
    """
    tags = [
        {"label": "意见内容", "value": _truncate(content, 300)},
        {"label": "项目亮点", "value": _truncate(highlights, 200)},
        {"label": "创新Idea", "value": _truncate(innovation_ideas, 200)},
        {"label": "指派部门", "value": dept_names or "无"},
    ]
    buttons = [
        {
            "text": "✅ 审批通过",
            "value": f"suggestion_approve_{assignment_id}",
            "type": "primary",
        },
        {
            "text": "❌ 驳回",
            "value": f"suggestion_reject_{assignment_id}",
            "type": "danger",
        },
    ]
    body = [
        {"tag": "hr"},
        {"tag": "button", "text": {"tag": "plain_text", "content": buttons[0]["text"]},
         "type": buttons[0]["type"], "width": "fill",
         "value": {"action": buttons[0]["value"]}},
        {"tag": "button", "text": {"tag": "plain_text", "content": buttons[1]["text"]},
         "type": buttons[1]["type"], "width": "fill",
         "value": {"action": buttons[1]["value"]}},
    ]
    card = _build_card("【匿名建议待审批】", tags=tags, body_elements=body, header_template="orange")

    msg_id = _send_with_retry(
        _get_feishu_service().send_message_to_user,
        suggestion_id=suggestion_id,
        open_id=open_id,
        card=card,
    )
    if msg_id is not None:
        logger.info(
            f"Suggestion pending card sent: suggestion={suggestion_id}, open_id={open_id}, msg_id={msg_id}",
            extra={"action": "suggestion.notify", "suggestion_id": suggestion_id, "message_id": msg_id},
        )
    return msg_id


async def send_pending_card(
    open_id: str,
    suggestion_id: int,
    assignment_id: int,
    content: str,
    highlights: str | None,
    innovation_ideas: str | None,
    dept_names: str,
) -> str | None:
    """Async wrapper for send_pending_card_sync (used by API endpoints)."""
    return await asyncio.to_thread(
        send_pending_card_sync,
        open_id, suggestion_id, assignment_id, content, highlights, innovation_ideas, dept_names,
    )


def update_to_approved_sync(open_message_id: str, approver_name: str) -> None:
    """Update the original card to approved (blue, no buttons). Sync version.

    ND-3 修复（第二轮审查）：用 _update_card_with_retry 包装，3 次指数退避重试。
    """
    tags = [
        {"label": "审批人", "value": approver_name or "未知"},
        {"label": "审批时间", "value": now_shanghai().strftime("%Y-%m-%d %H:%M")},
    ]
    body = [{"tag": "hr"}, {"tag": "div", "text": {"tag": "lark_md",
        "content": "**状态**：<font color='blue'>已审批通过，转市场部处理中</font>"}}]
    card = _build_card("【匿名建议已审批】", tags=tags, body_elements=body, header_template="blue")
    _update_card_with_retry(open_message_id, card, action="suggestion.update.approved")


async def update_to_approved(open_message_id: str, approver_name: str) -> None:
    """Async wrapper for update_to_approved_sync."""
    await asyncio.to_thread(update_to_approved_sync, open_message_id, approver_name)


def send_market_card_sync(
    open_id: str,
    suggestion_id: int,
    content: str,
    highlights: str | None,
    innovation_ideas: str | None,
    approver_name: str,
    approved_at_str: str,
) -> str | None:
    """Send the market-team card with an input form for execution result. Returns open_message_id.

    Sync version (used by callback handler threads).
    """
    tags = [
        {"label": "意见内容", "value": _truncate(content, 300)},
        {"label": "项目亮点", "value": _truncate(highlights, 200)},
        {"label": "创新Idea", "value": _truncate(innovation_ideas, 200)},
        {"label": "审批人", "value": approver_name or "未知"},
        {"label": "审批时间", "value": approved_at_str},
    ]
    # 表单：input + 提交存档按钮（参照 service.py update_card_to_handling 中已验证可用的格式）
    form_elements = [
        {
            "tag": "input",
            "name": "market_result",
            "placeholder": {"tag": "plain_text", "content": "请输入执行结果"},
        },
        {
            "tag": "button",
            "text": {"tag": "plain_text", "content": "📦 提交存档"},
            "type": "primary",
            "width": "fill",
            "name": f"suggestion_archive_{suggestion_id}",
            "form_action_type": "submit",
        },
    ]
    body = [{"tag": "hr"}, {"tag": "form", "name": "market_form", "elements": form_elements}]
    card = _build_card("【匿名建议待执行】", tags=tags, body_elements=body, header_template="blue")

    msg_id = _send_with_retry(
        _get_feishu_service().send_message_to_user,
        suggestion_id=suggestion_id,
        open_id=open_id,
        card=card,
    )
    if msg_id is not None:
        logger.info(
            f"Suggestion market card sent: suggestion={suggestion_id}, open_id={open_id}, msg_id={msg_id}",
            extra={"action": "suggestion.notify", "suggestion_id": suggestion_id, "message_id": msg_id},
        )
    return msg_id


async def send_market_card(
    open_id: str,
    suggestion_id: int,
    content: str,
    highlights: str | None,
    innovation_ideas: str | None,
    approver_name: str,
    approved_at_str: str,
) -> str | None:
    """Async wrapper for send_market_card_sync."""
    return await asyncio.to_thread(
        send_market_card_sync,
        open_id, suggestion_id, content, highlights, innovation_ideas, approver_name, approved_at_str,
    )


def update_to_archived_sync(open_message_id: str, market_result: str) -> None:
    """Update the market card to archived (green, no buttons). Sync version.

    ND-3 修复（第二轮审查）：用 _update_card_with_retry 包装，3 次指数退避重试。
    """
    tags = [
        {"label": "执行结果", "value": _truncate(market_result, 300)},
        {"label": "存档时间", "value": now_shanghai().strftime("%Y-%m-%d %H:%M")},
    ]
    body = [{"tag": "hr"}, {"tag": "div", "text": {"tag": "lark_md",
        "content": "**状态**：<font color='green'>已存档</font>"}}]
    card = _build_card("【匿名建议已存档】", tags=tags, body_elements=body, header_template="green")
    _update_card_with_retry(open_message_id, card, action="suggestion.update.archived")


async def update_to_archived(open_message_id: str, market_result: str) -> None:
    """Async wrapper for update_to_archived_sync."""
    await asyncio.to_thread(update_to_archived_sync, open_message_id, market_result)


def update_to_rejected_sync(open_message_id: str, reject_reason: str) -> None:
    """Update the original card to rejected (grey, no buttons). Sync version.

    ND-3 修复（第二轮审查）：用 _update_card_with_retry 包装，3 次指数退避重试。
    """
    tags = [
        {"label": "驳回原因", "value": _truncate(reject_reason, 300)},
    ]
    body = [{"tag": "hr"}, {"tag": "div", "text": {"tag": "lark_md",
        "content": "**状态**：<font color='grey'>已驳回</font>"}}]
    card = _build_card("【匿名建议已驳回】", tags=tags, body_elements=body, header_template="grey")
    _update_card_with_retry(open_message_id, card, action="suggestion.update.rejected")


async def update_to_rejected(open_message_id: str, reject_reason: str) -> None:
    """Async wrapper for update_to_rejected_sync."""
    await asyncio.to_thread(update_to_rejected_sync, open_message_id, reject_reason)


def status_text(status: str) -> str:
    """Map status code to Chinese text."""
    mapping = {
        SuggestionStatus.PENDING: "待审批",
        SuggestionStatus.APPROVED: "已审批通过，待市场部处理",
        SuggestionStatus.ARCHIVED: "已存档",
        SuggestionStatus.REJECTED: "已驳回",
    }
    return mapping.get(status, status)
