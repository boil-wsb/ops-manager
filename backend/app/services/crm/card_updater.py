"""CRM 同步飞书卡片状态更新模块。

提供 CRM 同步场景下飞书卡片的状态更新能力：
- 同步中：将按钮替换为"同步中"提示
- 同步成功：更新为成功状态卡片
- 同步失败：更新为失败状态卡片

由于飞书卡片回调在 WebSocket 线程中触发，回调线程无法 await，
因此提供同步版本（_sync 前缀）通过 asyncio.run 调用。
"""

import asyncio
from typing import Any

from app.core.logging import get_logger
from app.services.crm.sync_service import SYNC_TYPE_LABELS

logger = get_logger(__name__)


def _build_syncing_card(sync_type: str, original_card: dict | None = None) -> dict:
    """构建"同步中"状态卡片。

    保留原卡片结构，仅将触发按钮替换为同步中提示。
    """
    label = SYNC_TYPE_LABELS.get(sync_type, sync_type)
    card = {
        "schema": "2.0",
        "header": {
            "title": {"tag": "plain_text", "content": label},
            "template": "blue",
            "text_tag_list": [
                {
                    "element_id": "status_tag",
                    "tag": "text_tag",
                    "text": {"tag": "plain_text", "content": "同步中"},
                    "color": "blue",
                }
            ],
        },
        "body": {
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"⏳ **{label}** 正在执行，请稍候...",
                    },
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": "***当前状态***：<font color='blue'>同步中</font>",
                    },
                    "icon": {
                        "tag": "standard_icon",
                        "token": "time_outlined",
                        "color": "blue",
                    },
                },
            ]
        },
    }
    return card


def _build_success_card(sync_type: str, result: dict[str, Any]) -> dict:
    """构建"同步成功"状态卡片。"""
    label = SYNC_TYPE_LABELS.get(sync_type, sync_type)
    started_at = result.get("started_at", "")
    duration_ms = result.get("duration_ms", 0)
    status_code = result.get("status_code", "")

    # 格式化耗时显示
    if duration_ms:
        if duration_ms < 1000:
            duration_display = f"{duration_ms}ms"
        else:
            duration_display = f"{duration_ms / 1000:.2f}s"
    else:
        duration_display = "-"

    body_elements = [
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"✅ **{label}** 已完成",
            },
        },
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": "***当前状态***：<font color='green'>成功</font>",
            },
            "icon": {
                "tag": "standard_icon",
                "token": "check_circle_outlined",
                "color": "green",
            },
        },
        {
            "tag": "hr",
        },
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"🕐 **开始时间**：{started_at}",
            },
        },
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"⏱ **耗时**：{duration_display}",
            },
        },
    ]

    if status_code:
        body_elements.append(
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"📡 **HTTP状态**：{status_code}",
                },
            }
        )

    # 附加响应数据（如有）
    data = result.get("data")
    if data:
        try:
            import json

            data_str = json.dumps(data, ensure_ascii=False, default=str)
            if len(data_str) > 500:
                data_str = data_str[:500] + "..."
            body_elements.append(
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"📋 **响应数据**：\n```\n{data_str}\n```",
                    },
                }
            )
        except Exception:
            pass

    return {
        "schema": "2.0",
        "header": {
            "title": {"tag": "plain_text", "content": label},
            "template": "green",
            "text_tag_list": [
                {
                    "element_id": "status_tag",
                    "tag": "text_tag",
                    "text": {"tag": "plain_text", "content": "成功"},
                    "color": "green",
                }
            ],
        },
        "body": {"elements": body_elements},
    }


def _build_failed_card(sync_type: str, result: dict[str, Any]) -> dict:
    """构建"同步失败"状态卡片。"""
    label = SYNC_TYPE_LABELS.get(sync_type, sync_type)
    started_at = result.get("started_at", "")
    error_msg = result.get("error", "") or result.get("message", "")
    status_code = result.get("status_code", "")

    body_elements = [
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"❌ **{label}** 执行失败",
            },
        },
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": "***当前状态***：<font color='red'>失败</font>",
            },
            "icon": {
                "tag": "standard_icon",
                "token": "close_circle_outlined",
                "color": "red",
            },
        },
        {
            "tag": "hr",
        },
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"🕐 **开始时间**：{started_at}",
            },
        },
    ]

    if status_code:
        body_elements.append(
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"📡 **HTTP状态**：{status_code}",
                },
            }
        )

    if error_msg:
        error_display = error_msg[:500] if len(str(error_msg)) > 500 else str(error_msg)
        body_elements.append(
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"⚠️ **错误信息**：\n```\n{error_display}\n```",
                },
            }
        )

    return {
        "schema": "2.0",
        "header": {
            "title": {"tag": "plain_text", "content": label},
            "template": "red",
            "text_tag_list": [
                {
                    "element_id": "status_tag",
                    "tag": "text_tag",
                    "text": {"tag": "plain_text", "content": "失败"},
                    "color": "red",
                }
            ],
        },
        "body": {"elements": body_elements},
    }


async def _update_card(open_message_id: str, card_content: dict) -> bool:
    """异步更新飞书卡片内容。"""
    try:
        from app.services.alerts.feishu_notification import get_feishu_notification_service

        feishu_svc = get_feishu_notification_service()

        # 飞书 SDK 是同步调用，使用 asyncio.to_thread 避免阻塞事件循环
        result = await asyncio.to_thread(
            feishu_svc.update_card_message,
            open_message_id,
            card_content,
        )

        if result.get("success"):
            logger.info(
                f"CRM同步卡片已更新: open_message_id={open_message_id}",
                extra={
                    "action": "crm.sync.card_update",
                    "open_message_id": open_message_id,
                },
            )
            return True
        else:
            logger.warning(
                f"CRM同步卡片更新未成功: open_message_id={open_message_id}, error={result.get('error')}",
                extra={
                    "action": "crm.sync.card_update",
                    "open_message_id": open_message_id,
                    "error": result.get("error"),
                },
            )
            return False
    except Exception as e:
        logger.error(
            f"CRM同步卡片更新异常: {e}",
            extra={
                "action": "crm.sync.card_update",
                "open_message_id": open_message_id,
                "error": str(e),
            },
        )
        return False


async def update_card_to_syncing(open_message_id: str, sync_type: str) -> bool:
    """更新卡片为"同步中"状态。"""
    card = _build_syncing_card(sync_type)
    return await _update_card(open_message_id, card)


async def update_card_to_sync_result(
    open_message_id: str, sync_type: str, result: dict[str, Any]
) -> bool:
    """根据同步结果更新卡片为成功或失败状态。"""
    if result.get("success"):
        card = _build_success_card(sync_type, result)
    else:
        card = _build_failed_card(sync_type, result)
    return await _update_card(open_message_id, card)


def _update_card_sync(open_message_id: str, card_content: dict) -> bool:
    """同步更新飞书卡片内容（用于飞书回调线程中直接调用）。"""
    try:
        from app.services.alerts.feishu_notification import get_feishu_notification_service

        feishu_svc = get_feishu_notification_service()
        result = feishu_svc.update_card_message(open_message_id, card_content)

        if result.get("success"):
            logger.info(
                f"CRM同步卡片已更新（同步）: open_message_id={open_message_id}",
                extra={
                    "action": "crm.sync.card_update",
                    "open_message_id": open_message_id,
                },
            )
            return True
        else:
            logger.warning(
                f"CRM同步卡片更新未成功（同步）: open_message_id={open_message_id}, error={result.get('error')}",
                extra={
                    "action": "crm.sync.card_update",
                    "open_message_id": open_message_id,
                    "error": result.get("error"),
                },
            )
            return False
    except Exception as e:
        logger.error(
            f"CRM同步卡片更新异常（同步）: {e}",
            extra={
                "action": "crm.sync.card_update",
                "open_message_id": open_message_id,
                "error": str(e),
            },
        )
        return False


def update_card_to_syncing_sync(open_message_id: str, sync_type: str) -> bool:
    """同步版本的卡片更新（用于飞书回调线程中调用）。"""
    card = _build_syncing_card(sync_type)
    return _update_card_sync(open_message_id, card)


def update_card_to_sync_result_sync(
    open_message_id: str, sync_type: str, result: dict[str, Any]
) -> bool:
    """同步版本的卡片更新（用于飞书回调线程中调用）。"""
    if result.get("success"):
        card = _build_success_card(sync_type, result)
    else:
        card = _build_failed_card(sync_type, result)
    return _update_card_sync(open_message_id, card)


# ---------------------------------------------------------------------------
# 以下函数用于"文本消息触发 CRM 同步"场景：没有可更新的原卡片，
# 需要直接向用户发送新的卡片消息。
# ---------------------------------------------------------------------------


def _send_card_sync(open_id: str, card_content: dict) -> str | None:
    """同步发送新的飞书卡片消息给用户（用于飞书回调线程中直接调用）。

    与 _update_card_sync 的区别：本函数发送新卡片，而非更新已有卡片。

    Returns:
        成功时返回 message_id（可用于后续更新卡片），失败返回 None
    """
    try:
        from app.services.alerts.feishu_notification import get_feishu_notification_service

        feishu_svc = get_feishu_notification_service()
        result = feishu_svc.send_p2p_card_message(open_id=open_id, card_content=card_content)

        if result.get("success"):
            message_id = result.get("message_id")
            logger.info(
                f"CRM同步卡片已发送: open_id={open_id}, message_id={message_id}",
                extra={
                    "action": "crm.sync.card_send",
                    "open_id": open_id,
                    "message_id": message_id,
                },
            )
            return message_id
        else:
            logger.warning(
                f"CRM同步卡片发送未成功: open_id={open_id}",
                extra={"action": "crm.sync.card_send", "open_id": open_id},
            )
            return None
    except Exception as e:
        logger.error(
            f"CRM同步卡片发送异常: {e}",
            extra={"action": "crm.sync.card_send", "open_id": open_id, "error": str(e)},
        )
        return None


def send_syncing_card_sync(open_id: str, sync_type: str) -> str | None:
    """发送"同步中"状态的新卡片给用户，返回 message_id（可用于后续更新）。"""
    card = _build_syncing_card(sync_type)
    return _send_card_sync(open_id, card)


def send_sync_result_card_sync(open_id: str, sync_type: str, result: dict[str, Any]) -> str | None:
    """根据同步结果发送成功或失败状态的新卡片给用户，返回 message_id。"""
    if result.get("success"):
        card = _build_success_card(sync_type, result)
    else:
        card = _build_failed_card(sync_type, result)
    return _send_card_sync(open_id, card)
