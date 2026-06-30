"""
Feishu callback handler for long connection (WebSocket) mode.
"""

import json
import threading
from typing import Any

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

NOTIFICATION_TYPE_ALERT_TRANSFERRED_TO_IT = "alert_transferred_to_it"

_lark = None
_callback_thread: threading.Thread | None = None
_ws_client: Any = None

# CRM 同步任务进行中状态：sync_type -> True/False
# 用于去重：同步进行中再次收到相同指令时回复"已在同步中"，避免重复触发
_crm_sync_in_progress: dict[str, bool] = {}
_crm_sync_in_progress_lock = threading.Lock()


def _try_forward_callback(
    open_message_id: str | None,
    data: Any,
    button_action: str,
    value: dict | str,
    operator_open_id: str | None,
) -> None:
    # 提取 callback_id 用于查询
    callback_id = None
    if isinstance(value, dict):
        callback_id = value.get("callback_id")

    if not open_message_id and not callback_id:
        return

    try:
        from sqlalchemy import create_engine, text

        from app.config import settings

        sync_db_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
        engine = create_engine(sync_db_url, pool_pre_ping=True)

        record_id = None
        callback_url = None
        card_content = None

        with engine.connect() as conn:
            # 优先通过 callback_id 查找，其次通过 open_message_id
            if callback_id:
                result = conn.execute(
                    text(
                        "SELECT id, callback_url, card_content FROM notification_records "
                        "WHERE callback_id = :callback_id "
                        "ORDER BY id DESC LIMIT 1"
                    ),
                    {"callback_id": callback_id},
                )
                row = result.fetchone()
            if not row or not row[0]:
                row = None
                if open_message_id:
                    result = conn.execute(
                        text(
                            "SELECT id, callback_url, card_content FROM notification_records "
                            "WHERE open_message_id = :open_message_id "
                            "ORDER BY id DESC LIMIT 1"
                        ),
                        {"open_message_id": open_message_id},
                    )
                    row = result.fetchone()
            if row:
                record_id = row[0]
                callback_url = row[1]
                card_content = row[2]

        logger.info(
            f"回调查询记录: open_message_id={open_message_id}, callback_id={callback_id}, record_id={record_id}, "
            f"has_callback_url={callback_url is not None}, has_card_content={card_content is not None}",
            extra={
                "action": "feishu.callback.forward",
                "open_message_id": open_message_id,
                "callback_id": callback_id,
                "record_id": record_id,
                "card_content": card_content,
            },
        )

        # 处理转发给指定人的场景
        if button_action == "forward_to_assignee" and isinstance(value, dict):
            assignee_open_id = value.get("assignee_open_id")
            if assignee_open_id and card_content:
                import json

                card_dict = (
                    card_content if isinstance(card_content, dict) else json.loads(card_content)
                )
                logger.info(
                    f"转发卡片给指定用户: assignee_open_id={assignee_open_id}",
                    extra={
                        "action": "feishu.callback.forward",
                        "assignee_open_id": assignee_open_id,
                        "card_content": card_dict,
                    },
                )
                try:
                    from app.services.alerts.feishu_notification import (
                        get_feishu_notification_service,
                    )

                    feishu_svc = get_feishu_notification_service()
                    result = feishu_svc.send_p2p_card_message(
                        open_id=assignee_open_id,
                        card_content=card_dict,
                    )
                    if result.get("success"):
                        logger.info(
                            f"卡片转发成功: assignee_open_id={assignee_open_id}, message_id={result.get('message_id')}",
                            extra={
                                "action": "feishu.callback.forward",
                                "assignee_open_id": assignee_open_id,
                            },
                        )
                        # 更新原卡片：将"转交运维处理"按钮替换为"已转交运维"通知框
                        if open_message_id:
                            try:
                                import copy

                                updated_card = copy.deepcopy(card_dict)
                                elements = (
                                    updated_card.get("body", {}).get("elements", [])
                                    if isinstance(updated_card, dict)
                                    else []
                                )
                                for idx, el in enumerate(elements):
                                    if (
                                        isinstance(el, dict)
                                        and el.get("tag") == "button"
                                        and isinstance(el.get("value"), dict)
                                        and el.get("value", {}).get("action")
                                        == "forward_to_assignee"
                                    ):
                                        elements[idx] = {
                                            "tag": "markdown",
                                            "content": "***处理状态***：<font color='green'>✅ 已转交运维</font>",
                                            "text_align": "left",
                                            "text_size": "normal",
                                            "icon": {
                                                "tag": "standard_icon",
                                                "token": "check_circle_outlined",
                                                "color": "green",
                                            },
                                        }
                                        break
                                update_result = feishu_svc.update_card_message(
                                    open_message_id=open_message_id,
                                    card_content=updated_card,
                                )
                                if update_result.get("success"):
                                    logger.info(
                                        f"原卡片已更新为已转交运维状态: open_message_id={open_message_id}",
                                        extra={
                                            "action": "feishu.callback.forward",
                                            "open_message_id": open_message_id,
                                        },
                                    )
                                else:
                                    logger.warning(
                                        f"原卡片更新未成功: open_message_id={open_message_id}, error={update_result.get('error')}",
                                        extra={
                                            "action": "feishu.callback.forward",
                                            "open_message_id": open_message_id,
                                            "error": update_result.get("error"),
                                        },
                                    )
                            except Exception as update_err:
                                logger.error(
                                    f"更新原卡片为已转交运维状态失败: {update_err}",
                                    extra={
                                        "action": "feishu.callback.forward",
                                        "open_message_id": open_message_id,
                                        "error": str(update_err),
                                    },
                                )
                    else:
                        logger.warning(
                            f"卡片转发失败: assignee_open_id={assignee_open_id}",
                            extra={
                                "action": "feishu.callback.forward",
                                "assignee_open_id": assignee_open_id,
                            },
                        )
                except Exception as send_err:
                    logger.error(
                        f"发送转发卡片异常: {send_err}",
                        extra={
                            "action": "feishu.callback.forward",
                            "assignee_open_id": assignee_open_id,
                            "error": str(send_err),
                        },
                    )
            else:
                logger.warning(
                    f"转发缺少必要参数: assignee_open_id={assignee_open_id}, has_card_content={card_content is not None}",
                    extra={
                        "action": "feishu.callback.forward",
                        "assignee_open_id": assignee_open_id,
                    },
                )
            engine.dispose()
            return

        # 处理回调 URL 转发
        if not record_id or not callback_url:
            engine.dispose()
            return

        operator_info = {}
        if hasattr(data.event, "operator") and data.event.operator:
            op = data.event.operator
            operator_info = {
                "open_id": getattr(op, "open_id", None)
                or (getattr(getattr(op, "operator_id", None), "open_id", None)),
                "user_id": getattr(op, "user_id", None)
                or (getattr(getattr(op, "operator_id", None), "user_id", None)),
                "union_id": getattr(op, "union_id", None),
            }

        open_chat_id = None
        if hasattr(data.event, "context") and data.event.context:
            open_chat_id = getattr(data.event.context, "open_chat_id", None)

        callback_data = {
            "open_message_id": open_message_id,
            "open_chat_id": open_chat_id,
            "operator": {k: v for k, v in operator_info.items() if v is not None},
            "action": {
                "tag": "button",
                "value": value if isinstance(value, dict) else {"action": str(value)},
            },
            "callback_id": value.get("callback_id") if isinstance(value, dict) else None,
            "timestamp": __import__("datetime")
            .datetime.now(tz=__import__("datetime").timezone.utc)
            .isoformat(),
        }

        import httpx

        with httpx.Client(timeout=5.0) as client:
            response = client.post(callback_url, json=callback_data)

        with engine.connect() as conn:
            conn.execute(
                text(
                    "INSERT INTO notification_callback_logs "
                    "(notification_record_id, callback_url, request_body, response_status, response_body, status, created_at) "
                    "VALUES (:record_id, :callback_url, :request_body, :response_status, :response_body, 'success', NOW())"
                ),
                {
                    "record_id": record_id,
                    "callback_url": callback_url,
                    "request_body": __import__("json").dumps(callback_data, ensure_ascii=False),
                    "response_status": response.status_code,
                    "response_body": response.text[:2000],
                },
            )
            conn.commit()

        logger.info(
            f"回调转发成功: {callback_url}",
            extra={
                "action": "feishu.callback.forward",
                "callback_url": callback_url,
                "status_code": response.status_code,
            },
        )

        engine.dispose()

    except Exception as e:
        logger.warning(
            f"回调转发失败: {e}",
            extra={
                "action": "feishu.callback.forward",
                "error": str(e),
                "open_message_id": open_message_id,
            },
        )
        try:
            from sqlalchemy import create_engine as _create_engine
            from sqlalchemy import text as _text

            from app.config import settings as _settings

            _sync_db_url = _settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
            _engine = _create_engine(_sync_db_url, pool_pre_ping=True)

            with _engine.connect() as conn:
                conn.execute(
                    _text(
                        "INSERT INTO notification_callback_logs "
                        "(notification_record_id, callback_url, request_body, status, error_message, created_at) "
                        "VALUES (:record_id, :callback_url, :request_body, 'failed', :error_message, NOW())"
                    ),
                    {
                        "record_id": record_id if "record_id" in dir() else None,
                        "callback_url": callback_url if "callback_url" in dir() else "",
                        "request_body": __import__("json").dumps(callback_data, ensure_ascii=False)
                        if "callback_data" in dir()
                        else None,
                        "error_message": str(e),
                    },
                )
                conn.commit()
            _engine.dispose()
        except Exception as log_err:
            logger.error(f"记录回调失败日志出错: {log_err}")


def _record_interaction(**kwargs) -> None:
    try:
        from app.crud.crud_feishu_interaction import record_interaction_sync

        record_interaction_sync(**kwargs)
    except Exception as e:
        logger.error(f"记录飞书交互失败: {e}", extra={"action": "feishu.callback", "error": str(e)})


def _get_lark_module():
    global _lark
    if _lark is None:
        import lark_oapi as lark

        _lark = lark
    return _lark


def _do_card_action_trigger(data: Any) -> Any:
    """Handle card action trigger callback."""
    lark = _get_lark_module()
    data_str = lark.JSON.marshal(data)
    action_tag = (
        getattr(data.event.action, "tag", None)
        if hasattr(data, "event") and hasattr(data.event, "action")
        else None
    )
    logger.info(
        f"收到卡片回调: action={action_tag}",
        extra={"action": "feishu.callback", "callback_data": data_str},
    )

    try:
        action = data.event.action
        action_tag = getattr(action, "tag", None)
        value = action.value if hasattr(action, "value") and action.value else {}
        form_value = getattr(action, "form_value", None)
        input_value = getattr(action, "input_value", None)
        name = getattr(action, "name", None)

        operator_open_id = None
        if hasattr(data.event, "operator") and data.event.operator:
            operator_id = getattr(data.event.operator, "operator_id", None)
            if operator_id:
                operator_open_id = getattr(operator_id, "open_id", None) or getattr(
                    operator_id, "user_id", None
                )

        if action_tag == "input":
            logger.info("忽略输入框回调，等待表单提交", extra={"action": "feishu.callback"})
            from lark_oapi.event.callback.model.p2_card_action_trigger import (
                P2CardActionTriggerResponse,
            )

            return P2CardActionTriggerResponse(None)

        button_action = value.get("action", "") if isinstance(value, dict) else ""
        if not button_action and name:
            button_action = name

        # 获取按钮文本，用于按文本识别 CRM 同步动作
        button_text = ""
        if hasattr(action, "text") and action.text:
            button_text = getattr(action.text, "content", "") or str(action.text)
        elif hasattr(action, "option") and action.option:
            opt_text = getattr(action.option, "text", None)
            if opt_text:
                button_text = getattr(opt_text, "content", "") or str(opt_text)

        logger.info(
            f"按钮回调详情: button_action={button_action}, button_text={button_text}, "
            f"value={value}, name={name}",
            extra={
                "action": "feishu.callback",
                "button_action": button_action,
                "button_text": button_text,
                "value": value if isinstance(value, dict) else str(value),
            },
        )

        # 如果 button_action 未匹配 CRM 同步，但按钮文本是"CRM 增量同步"/"CRM 全量同步"，也触发
        if button_action not in ("crm_sync_incremental", "crm_sync_full"):
            if "增量" in button_text and "CRM" in button_text.upper():
                button_action = "crm_sync_incremental"
                logger.info(
                    f"根据按钮文本识别为 CRM 增量同步: button_text={button_text}",
                    extra={"action": "feishu.callback", "button_text": button_text},
                )
            elif "全量" in button_text and "CRM" in button_text.upper():
                button_action = "crm_sync_full"
                logger.info(
                    f"根据按钮文本识别为 CRM 全量同步: button_text={button_text}",
                    extra={"action": "feishu.callback", "button_text": button_text},
                )

        open_message_id = None
        if hasattr(data.event, "context") and data.event.context:
            open_message_id = (
                data.event.context.open_message_id
                if hasattr(data.event.context, "open_message_id")
                else None
            )

        related_type = None
        related_id = None
        if button_action.startswith("handle_"):
            related_type = "it_feedback"
            related_id = button_action.replace("handle_", "")
        elif button_action == "submit_resolution":
            related_type = "it_feedback"
            feedback_id_from_value = value.get("feedback_id") if isinstance(value, dict) else None
            if feedback_id_from_value:
                related_id = str(feedback_id_from_value)
            elif open_message_id:
                related_id = _get_feedback_id_by_open_message_id(open_message_id)
        elif button_action.startswith("acknowledge_"):
            related_type = "alert"
            related_id = button_action.replace("acknowledge_", "")
        elif button_action.startswith("transfer_it_"):
            related_type = "alert"
            related_id = button_action.replace("transfer_it_", "")
        elif button_action == "resolve_alert":
            related_type = "alert"
            alert_id_from_value = value.get("alert_id") if isinstance(value, dict) else None
            if alert_id_from_value:
                related_id = str(alert_id_from_value)
            elif open_message_id:
                related_id = _get_alert_id_by_open_message_id(open_message_id)
        elif button_action in ("crm_sync_incremental", "crm_sync_full"):
            related_type = "crm_sync"
            related_id = button_action.replace("crm_sync_", "")

        _record_interaction(
            direction="inbound",
            interaction_type="card_action",
            feishu_open_id=operator_open_id,
            message_id=open_message_id,
            content={
                "action": button_action,
                "value": value if isinstance(value, dict) else str(value),
            },
            action_type=button_action,
            related_type=related_type,
            related_id=related_id,
        )

        if button_action.startswith("handle_"):
            feedback_id = button_action.replace("handle_", "")
            threading.Thread(target=_handle_feedback_sync, args=(feedback_id,), daemon=True).start()

            if open_message_id:
                threading.Thread(
                    target=_update_card_to_handling,
                    args=(open_message_id, feedback_id),
                    daemon=True,
                ).start()

            resp = {"toast": {"type": "info", "content": "已开始处理，请填写处理方式"}}

        elif button_action == "submit_resolution":
            feedback_id_from_value = value.get("feedback_id") if isinstance(value, dict) else None
            notes = ""
            if form_value and isinstance(form_value, dict):
                notes = form_value.get("notes", "") or ""
            if not notes and input_value and isinstance(input_value, dict):
                notes = input_value.get("notes", "") or ""

            feedback_id = None
            if feedback_id_from_value:
                feedback_id = str(feedback_id_from_value)
            elif open_message_id:
                feedback_id = _get_feedback_id_by_open_message_id(open_message_id)

            if not feedback_id:
                resp = {"toast": {"type": "error", "content": "无法找到反馈记录"}}
                from lark_oapi.event.callback.model.p2_card_action_trigger import (
                    P2CardActionTriggerResponse,
                )

                return P2CardActionTriggerResponse(resp)

            logger.info(
                f"完成反馈处理: {feedback_id}",
                extra={"action": "feishu.callback", "feedback_id": feedback_id, "notes": notes},
            )

            if not notes or not notes.strip():
                resp = {"toast": {"type": "error", "content": "请填写处理方式"}}
                from lark_oapi.event.callback.model.p2_card_action_trigger import (
                    P2CardActionTriggerResponse,
                )

                return P2CardActionTriggerResponse(resp)

            threading.Thread(
                target=_finish_feedback_sync, args=(feedback_id, notes), daemon=True
            ).start()

            if open_message_id:
                threading.Thread(
                    target=_update_card_to_resolved,
                    args=(open_message_id, feedback_id, notes),
                    daemon=True,
                ).start()
            resp = {"toast": {"type": "info", "content": "处理完成，已通知提交者"}}

        elif button_action.startswith("acknowledge_"):
            alert_id = button_action.replace("acknowledge_", "")
            threading.Thread(
                target=_acknowledge_alert, args=(alert_id, open_message_id), daemon=True
            ).start()
            resp = {"toast": {"type": "info", "content": "已接单，请填写处理方式"}}

        elif button_action.startswith("transfer_it_"):
            alert_id = button_action.replace("transfer_it_", "")
            threading.Thread(
                target=_transfer_alert_to_it, args=(alert_id, open_message_id), daemon=True
            ).start()
            resp = {"toast": {"type": "info", "content": "已转交 IT 处理"}}

        elif button_action == "resolve_alert":
            notes = ""
            if form_value and isinstance(form_value, dict):
                notes = form_value.get("alert_notes", "") or ""
            if not notes and input_value and isinstance(input_value, dict):
                notes = input_value.get("alert_notes", "") or ""

            if not notes or not notes.strip():
                resp = {"toast": {"type": "error", "content": "请填写处理方式"}}
                from lark_oapi.event.callback.model.p2_card_action_trigger import (
                    P2CardActionTriggerResponse,
                )

                return P2CardActionTriggerResponse(resp)

            alert_id_from_value = value.get("alert_id") if isinstance(value, dict) else None
            if not alert_id_from_value and open_message_id:
                alert_id_from_value = _get_alert_id_by_open_message_id(open_message_id)

            if alert_id_from_value:
                threading.Thread(
                    target=_resolve_alert_sync,
                    args=(str(alert_id_from_value), notes, open_message_id),
                    daemon=True,
                ).start()
                resp = {"toast": {"type": "info", "content": "告警已解决"}}
            else:
                resp = {"toast": {"type": "error", "content": "无法找到告警记录"}}

        elif button_action in ("crm_sync_incremental", "crm_sync_full"):
            sync_type = "incremental" if button_action == "crm_sync_incremental" else "full"
            sync_label_text = "增量" if sync_type == "incremental" else "全量"
            threading.Thread(
                target=_run_crm_sync_sync,
                args=(sync_type, open_message_id, operator_open_id),
                daemon=True,
            ).start()
            resp = {"toast": {"type": "info", "content": f"已触发 CRM {sync_label_text}同步"}}

        else:
            _try_forward_callback(open_message_id, data, button_action, value, operator_open_id)
            resp = {"toast": {"type": "info", "content": f"收到回调: {button_action}"}}

        from lark_oapi.event.callback.model.p2_card_action_trigger import (
            P2CardActionTriggerResponse,
        )

        return P2CardActionTriggerResponse(resp)

    except Exception as e:
        logger.error(f"处理卡片动作失败: {e}", extra={"action": "feishu.callback", "error": str(e)})
        resp = {"toast": {"type": "error", "content": f"处理失败: {str(e)}"}}
        from lark_oapi.event.callback.model.p2_card_action_trigger import (
            P2CardActionTriggerResponse,
        )

        return P2CardActionTriggerResponse(resp)


def _run_crm_sync_sync(
    sync_type: str,
    open_message_id: str | None,
    operator_open_id: str | None,
) -> None:
    """在飞书回调线程中执行 CRM 同步并更新卡片状态。

    流程：
    1. 更新卡片为"同步中"
    2. 同步执行 CRM 同步调用
    3. 根据结果更新卡片为"成功"或"失败"

    所有异常都在顶层捕获并记录，避免线程静默失败。
    """
    label = sync_type
    try:
        from app.services.crm.card_updater import (
            update_card_to_sync_result_sync,
            update_card_to_syncing_sync,
        )
        from app.services.crm.sync_service import (
            SYNC_TYPE_LABELS,
            SYNC_TYPE_PATHS,
            get_crm_sync_service,
        )

        label = SYNC_TYPE_LABELS.get(sync_type, sync_type)
        logger.info(
            f"[CRM回调] 开始执行: sync_type={sync_type}, open_message_id={open_message_id}, operator={operator_open_id}",
            extra={
                "action": "crm.sync.callback",
                "sync_type": sync_type,
                "open_message_id": open_message_id,
                "operator_open_id": operator_open_id,
            },
        )

        # 1. 更新卡片为同步中
        if open_message_id:
            try:
                logger.info(
                    f"[CRM回调] 步骤1: 更新卡片为同步中状态",
                    extra={
                        "action": "crm.sync.callback",
                        "step": "update_card_syncing",
                        "open_message_id": open_message_id,
                    },
                )
                update_card_to_syncing_sync(open_message_id, sync_type)
                logger.info(
                    f"[CRM回调] 步骤1完成: 卡片已更新为同步中",
                    extra={
                        "action": "crm.sync.callback",
                        "step": "update_card_syncing_done",
                        "open_message_id": open_message_id,
                    },
                )
            except Exception as e:
                logger.warning(
                    f"[CRM回调] 步骤1失败: 更新卡片为同步中状态失败: {e}",
                    extra={
                        "action": "crm.sync.callback",
                        "step": "update_card_syncing_error",
                        "open_message_id": open_message_id,
                        "error": str(e),
                    },
                )

        # 2. 同步执行 CRM 调用
        logger.info(
            f"[CRM回调] 步骤2: 获取 CRM 同步服务实例",
            extra={
                "action": "crm.sync.callback",
                "step": "get_service",
            },
        )
        service = get_crm_sync_service()
        logger.info(
            f"[CRM回调] 步骤2: CRM 服务配置 base_url={service.base_url}, timeout={service.timeout}",
            extra={
                "action": "crm.sync.callback",
                "step": "service_config",
                "base_url": service.base_url,
                "timeout": service.timeout,
            },
        )

        # 显式构建 URL 并记录，便于排查
        url = service._build_url(sync_type)
        logger.info(
            f"[CRM回调] 步骤2: 即将调用 CRM 接口: {url}",
            extra={
                "action": "crm.sync.callback",
                "step": "call_crm_api",
                "url": url,
                "sync_type": sync_type,
            },
        )

        result = service.trigger_sync_sync(sync_type)
        logger.info(
            f"[CRM回调] 步骤2完成: success={result.get('success')}, status_code={result.get('status_code')}, duration_ms={result.get('duration_ms')}",
            extra={
                "action": "crm.sync.callback",
                "step": "call_crm_api_done",
                "sync_type": sync_type,
                "success": result.get("success"),
                "status_code": result.get("status_code"),
                "duration_ms": result.get("duration_ms"),
            },
        )

        # 3. 更新卡片为最终结果
        if open_message_id:
            try:
                logger.info(
                    f"[CRM回调] 步骤3: 更新卡片为最终结果",
                    extra={
                        "action": "crm.sync.callback",
                        "step": "update_card_result",
                        "open_message_id": open_message_id,
                    },
                )
                update_card_to_sync_result_sync(open_message_id, sync_type, result)
                logger.info(
                    f"[CRM回调] 步骤3完成: 卡片已更新为最终结果",
                    extra={
                        "action": "crm.sync.callback",
                        "step": "update_card_result_done",
                        "open_message_id": open_message_id,
                    },
                )
            except Exception as e:
                logger.error(
                    f"[CRM回调] 步骤3失败: 更新卡片为最终结果状态失败: {e}",
                    extra={
                        "action": "crm.sync.callback",
                        "step": "update_card_result_error",
                        "open_message_id": open_message_id,
                        "error": str(e),
                    },
                )

        logger.info(
            f"[CRM回调] {label} 全流程完成: success={result.get('success')}",
            extra={
                "action": "crm.sync.callback",
                "step": "all_done",
                "sync_type": sync_type,
                "success": result.get("success"),
                "open_message_id": open_message_id,
            },
        )

    except Exception as e:
        logger.error(
            f"[CRM回调] {label} 执行异常（顶层捕获）: {e}",
            extra={
                "action": "crm.sync.callback",
                "step": "top_level_error",
                "sync_type": sync_type,
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )


def _handle_feedback_sync(feedback_id: str) -> None:
    """Mark feedback as handling using sync database operations."""
    from sqlalchemy import create_engine, text

    from app.config import settings

    try:
        sync_db_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
        engine = create_engine(sync_db_url, pool_pre_ping=True)

        with engine.connect() as conn:
            conn.execute(
                text("UPDATE it_feedbacks SET status = 'handling' WHERE id = :id"),
                {"id": int(feedback_id)},
            )
            conn.commit()
            logger.info(
                f"反馈 {feedback_id} 标记为处理中",
                extra={"action": "feishu.callback", "feedback_id": feedback_id},
            )
        engine.dispose()
    except Exception as e:
        logger.error(
            f"处理反馈失败: {feedback_id}",
            extra={"action": "feishu.callback", "feedback_id": feedback_id, "error": str(e)},
        )


def _get_feedback_id_by_open_message_id(open_message_id: str) -> str | None:
    """Get feedback ID by open_message_id."""
    from sqlalchemy import create_engine, text

    from app.config import settings

    try:
        sync_db_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
        engine = create_engine(sync_db_url, pool_pre_ping=True)

        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT id FROM it_feedbacks WHERE open_message_id = :open_message_id"),
                {"open_message_id": open_message_id},
            )
            row = result.fetchone()
        engine.dispose()
        if row:
            return str(row[0])
        return None
    except Exception as e:
        logger.error(
            f"通过open_message_id查询feedback_id失败: {open_message_id}",
            extra={
                "action": "feishu.callback",
                "open_message_id": open_message_id,
                "error": str(e),
            },
        )
        return None


def _finish_feedback_sync(feedback_id: str, notes: str) -> None:
    """Mark feedback as resolved with notes and notify the asset responsible person."""
    from sqlalchemy import create_engine, text

    from app.config import settings

    try:
        sync_db_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
        engine = create_engine(sync_db_url, pool_pre_ping=True)

        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT f.client_ip, f.description, a.customer, u.feishu_open_id, COALESCE(u.full_name, u.username) as resolver_name
                    FROM it_feedbacks f
                    LEFT JOIN assets a ON a.ip_address = f.client_ip
                    LEFT JOIN users u ON u.username = a.customer
                    WHERE f.id = :id
                """),
                {"id": int(feedback_id)},
            )
            row = result.fetchone()
            row[0] if row else None
            description = row[1] if row else ""
            customer = row[2] if row else None
            feishu_open_id = row[3] if row else None
            resolver_name = row[4] if row else "IT管理员"

            conn.execute(
                text("UPDATE it_feedbacks SET status = 'resolved', notes = :notes WHERE id = :id"),
                {"id": int(feedback_id), "notes": notes},
            )
            conn.commit()
            logger.info(
                f"反馈 {feedback_id} 已解决",
                extra={"action": "feishu.callback", "feedback_id": feedback_id, "notes": notes},
            )
        engine.dispose()

        if feishu_open_id:
            try:
                from app.integrations.feishu.service import get_feishu_service

                feishu = get_feishu_service()
                feishu.send_it_feedback_resolved(
                    user_id=feishu_open_id,
                    feedback_id=int(feedback_id),
                    feedback_content=description or "",
                    resolved_by=resolver_name,
                    notes=notes,
                )
                logger.info(
                    f"已发送通知: feishu_open_id={feishu_open_id}, feedback_id={feedback_id}",
                    extra={
                        "action": "feishu.callback",
                        "feishu_open_id": feishu_open_id,
                        "feedback_id": feedback_id,
                    },
                )
            except Exception as e:
                logger.error(
                    f"发送通知失败: {e}", extra={"action": "feishu.callback", "error": str(e)}
                )
        else:
            logger.warning(
                f"未找到飞书open_id: customer={customer}, 跳过通知",
                extra={"action": "feishu.callback", "customer": customer},
            )

    except Exception as e:
        logger.error(
            f"完成反馈失败: {feedback_id}",
            extra={"action": "feishu.callback", "feedback_id": feedback_id, "error": str(e)},
        )


def _resolve_feedback_sync(feedback_id: str) -> None:
    """Mark feedback as resolved using sync database operations."""
    from sqlalchemy import create_engine, text

    from app.config import settings

    try:
        sync_db_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
        engine = create_engine(sync_db_url, pool_pre_ping=True)

        with engine.connect() as conn:
            conn.execute(
                text("UPDATE it_feedbacks SET status = 'resolved' WHERE id = :id"),
                {"id": int(feedback_id)},
            )
            conn.commit()
            logger.info(
                f"反馈 {feedback_id} 标记为已解决",
                extra={"action": "feishu.callback", "feedback_id": feedback_id},
            )
        engine.dispose()
    except Exception as e:
        logger.error(
            f"解决反馈失败: {feedback_id}",
            extra={"action": "feishu.callback", "feedback_id": feedback_id, "error": str(e)},
        )


def _update_card_to_handling(open_message_id: str, feedback_id: str) -> None:
    """Update card to handling status with finish button."""
    from sqlalchemy import create_engine, text

    from app.config import settings
    from app.integrations.feishu.service import get_feishu_service

    try:
        sync_db_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
        engine = create_engine(sync_db_url, pool_pre_ping=True)

        responsible_name = None
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT a.owner_name FROM it_feedbacks f
                    LEFT JOIN assets a ON a.ip_address = f.client_ip
                    WHERE f.id = :id
                """),
                {"id": int(feedback_id)},
            )
            row = result.fetchone()
            responsible_name = row[0] if row else None
        engine.dispose()

        feishu = get_feishu_service()
        feishu.update_card_to_handling(open_message_id, feedback_id, responsible_name)
    except Exception as e:
        logger.error(
            f"更新卡片为处理中状态失败: {e}", extra={"action": "feishu.callback", "error": str(e)}
        )


def _update_card_to_resolved(open_message_id: str, feedback_id: str, notes: str) -> None:
    """Update card to resolved status."""
    from sqlalchemy import create_engine, text

    from app.config import settings
    from app.integrations.feishu.service import get_feishu_service

    try:
        sync_db_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
        engine = create_engine(sync_db_url, pool_pre_ping=True)

        responsible_name = None
        client_ip = None
        terminal_name = None
        description = None
        contact = None
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT a.owner_name, f.client_ip, a.name, f.description, f.contact
                    FROM it_feedbacks f
                    LEFT JOIN assets a ON a.ip_address = f.client_ip
                    WHERE f.id = :id
                """),
                {"id": int(feedback_id)},
            )
            row = result.fetchone()
            if row:
                responsible_name = row[0]
                client_ip = row[1]
                terminal_name = row[2]
                description = row[3]
                contact = row[4]
        engine.dispose()

        feishu = get_feishu_service()
        feishu.update_card_to_resolved(
            open_message_id=open_message_id,
            feedback_id=feedback_id,
            notes=notes,
            responsible_name=responsible_name,
            client_ip=client_ip,
            terminal_name=terminal_name,
            description=description,
            contact=contact,
        )
    except Exception as e:
        logger.error(
            f"更新卡片为已解决状态失败: {e}", extra={"action": "feishu.callback", "error": str(e)}
        )


def _get_alert_id_by_open_message_id(open_message_id: str) -> str | None:
    """Get alert ID by open_message_id from alert_history table."""
    from sqlalchemy import create_engine, text

    from app.config import settings

    try:
        sync_db_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
        engine = create_engine(sync_db_url, pool_pre_ping=True)

        with engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT alertname, labels->>'instance' as instance FROM alert_history WHERE feishu_open_message_id = :open_message_id AND status = 'firing' ORDER BY id DESC LIMIT 1"
                ),
                {"open_message_id": open_message_id},
            )
            row = result.fetchone()
        engine.dispose()
        if row:
            alertname = row[0] or ""
            instance = (row[1] or "").replace(".", "_")
            return f"{alertname}_{instance}"
        return None
    except Exception as e:
        logger.error(
            f"通过open_message_id查询alert_id失败: {open_message_id}",
            extra={
                "action": "feishu.callback",
                "open_message_id": open_message_id,
                "error": str(e),
            },
        )
        return None


def _acknowledge_alert(alert_id: str, open_message_id: str | None) -> None:
    """Mark alert as acknowledged and update card to show input form."""
    from sqlalchemy import create_engine, text

    from app.config import settings
    from app.integrations.feishu.service import get_feishu_service

    try:
        sync_db_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
        engine = create_engine(sync_db_url, pool_pre_ping=True)

        alertname = ""
        severity = ""
        instance = ""
        history_id = None

        with engine.connect() as conn:
            if open_message_id:
                result = conn.execute(
                    text(
                        "SELECT id, alertname, severity, labels->>'instance' as instance FROM alert_history WHERE feishu_open_message_id = :msg_id AND status = 'firing' ORDER BY id DESC LIMIT 1"
                    ),
                    {"msg_id": open_message_id},
                )
            else:
                parts = alert_id.rsplit("_", 1)
                if len(parts) == 2:
                    alertname_part, instance_part = parts
                    result = conn.execute(
                        text(
                            "SELECT id, alertname, severity, labels->>'instance' as instance FROM alert_history WHERE alertname = :name AND labels->>'instance' = :instance AND status = 'firing' ORDER BY id DESC LIMIT 1"
                        ),
                        {"name": alertname_part, "instance": instance_part.replace("_", ".")},
                    )
                else:
                    result = None

            if result:
                row = result.fetchone()
                if row:
                    history_id = row[0]
                    alertname = row[1] or ""
                    severity = row[2] or ""
                    instance = row[3] or ""

        if history_id and open_message_id:
            feishu = get_feishu_service()
            feishu.update_alert_card_to_acknowledged(
                open_message_id=open_message_id,
                alertname=alertname,
                severity=severity,
                instance=instance,
            )
            logger.info(
                f"告警卡片 {alert_id} 已更新为接单状态",
                extra={"action": "feishu.callback", "alert_id": alert_id},
            )
    except Exception as e:
        logger.error(
            f"接单失败: {alert_id}",
            extra={"action": "feishu.callback", "alert_id": alert_id, "error": str(e)},
        )


def _send_transfer_notification(
    alert_id: str, alertname: str, severity: str, instance: str
) -> None:
    """Send notification to IT team members when alert is transferred."""
    from sqlalchemy import create_engine, text

    from app.config import settings

    try:
        sync_db_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
        engine = create_engine(sync_db_url, pool_pre_ping=True)

        with engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT u.feishu_open_id FROM users u "
                    "JOIN notification_group_members ngm ON u.id = ngm.user_id "
                    "JOIN notification_groups ng ON ngm.notification_group_id = ng.id "
                    "WHERE ng.notification_type = :notif_type AND ng.is_active = true "
                    "AND u.feishu_open_id IS NOT NULL"
                ),
                {"notif_type": NOTIFICATION_TYPE_ALERT_TRANSFERRED_TO_IT},
            )
            rows = result.fetchall()

        for row in rows:
            user_id = row[0]
            if user_id:
                _send_transfer_card_to_user(user_id, alert_id, alertname, severity, instance)
    except Exception as e:
        logger.error(f"发送转交通知失败: {e}", extra={"action": "feishu.callback", "error": str(e)})


def _send_transfer_card_to_user(
    user_id: str, alert_id: str, alertname: str, severity: str, instance: str
) -> None:
    """Send alert transferred notification card to a single user."""
    try:
        from app.integrations.feishu.service import get_feishu_service

        tags = [
            {"label": "告警名称", "value": alertname or "未知"},
            {"label": "严重程度", "value": severity or "info"},
            {"label": "故障主机", "value": instance or "未知"},
        ]

        feishu = get_feishu_service()
        result = feishu.send_interactive_message(
            user_id=user_id,
            title=f"【{severity}】告警转交 IT 处理",
            content="",
            tags=tags,
            header_template="orange",
        )
        if isinstance(result, dict) and result.get("message_id"):
            logger.info(
                f"转交通知已发送: user_id={user_id}, message_id={result.get('message_id')}",
                extra={"action": "feishu.callback", "user_id": user_id},
            )
        else:
            logger.warning(
                f"转交通知发送失败: {user_id}",
                extra={"action": "feishu.callback", "user_id": user_id},
            )
    except Exception as e:
        logger.error(
            f"发送转交卡片失败: {user_id}",
            extra={"action": "feishu.callback", "user_id": user_id, "error": str(e)},
        )


def _transfer_alert_to_it(alert_id: str, open_message_id: str | None) -> None:
    """Transfer alert to IT and update card to show transferred status."""
    from sqlalchemy import create_engine, text

    from app.config import settings
    from app.integrations.feishu.service import get_feishu_service

    try:
        sync_db_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
        engine = create_engine(sync_db_url, pool_pre_ping=True)

        alertname = ""
        severity = ""
        instance = ""
        history_id = None

        with engine.connect() as conn:
            if open_message_id:
                result = conn.execute(
                    text(
                        "SELECT id, alertname, severity, labels->>'instance' as instance FROM alert_history WHERE feishu_open_message_id = :msg_id AND status = 'firing' ORDER BY id DESC LIMIT 1"
                    ),
                    {"msg_id": open_message_id},
                )
            else:
                parts = alert_id.rsplit("_", 1)
                if len(parts) == 2:
                    alertname_part, instance_part = parts
                    result = conn.execute(
                        text(
                            "SELECT id, alertname, severity, labels->>'instance' as instance FROM alert_history WHERE alertname = :name AND labels->>'instance' = :instance AND status = 'firing' ORDER BY id DESC LIMIT 1"
                        ),
                        {"name": alertname_part, "instance": instance_part.replace("_", ".")},
                    )
                else:
                    result = None

            if result:
                row = result.fetchone()
                if row:
                    history_id = row[0]
                    alertname = row[1] or ""
                    severity = row[2] or ""
                    instance = row[3] or ""

        if history_id and open_message_id:
            feishu = get_feishu_service()
            feishu.update_alert_card_to_transferred(
                open_message_id=open_message_id,
                alertname=alertname,
                severity=severity,
                instance=instance,
            )
            logger.info(
                f"告警卡片 {alert_id} 已更新为转交状态",
                extra={"action": "feishu.callback", "alert_id": alert_id},
            )

        _send_transfer_notification(alert_id, alertname, severity, instance)
    except Exception as e:
        logger.error(
            f"转交告警失败: {alert_id}",
            extra={"action": "feishu.callback", "alert_id": alert_id, "error": str(e)},
        )


def _resolve_alert_sync(alert_id: str, notes: str, open_message_id: str | None = None) -> None:
    """Mark alert as resolved with notes using sync database operations."""
    from sqlalchemy import create_engine, text

    from app.config import settings
    from app.services.alerts.feishu_notification import get_feishu_notification_service

    try:
        sync_db_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
        engine = create_engine(sync_db_url, pool_pre_ping=True)

        with engine.connect() as conn:
            if open_message_id:
                result = conn.execute(
                    text(
                        "SELECT id, alertname, labels->>'instance' as instance, feishu_open_message_id, severity FROM alert_history WHERE feishu_open_message_id = :msg_id AND status = 'firing' ORDER BY id DESC LIMIT 1"
                    ),
                    {"msg_id": open_message_id},
                )
                row = result.fetchone()
                if row:
                    history_id = row[0]
                    alertname = row[1] or ""
                    instance = row[2] or ""
                    feishu_open_message_id = row[3]
                    severity = row[4] or "warning"
                else:
                    alertname, instance, feishu_open_message_id, severity = "", "", None, "warning"
                    history_id = None
            else:
                parts = alert_id.rsplit("_", 1)
                if len(parts) == 2:
                    alertname_part, instance_part = parts
                    instance = instance_part.replace("_", ".")
                    result = conn.execute(
                        text(
                            "SELECT id, feishu_open_message_id, severity FROM alert_history WHERE alertname = :name AND labels->>'instance' = :instance AND status = 'firing' ORDER BY id DESC LIMIT 1"
                        ),
                        {"name": alertname_part, "instance": instance},
                    )
                    row = result.fetchone()
                    if row:
                        history_id = row[0]
                        feishu_open_message_id = row[1]
                        severity = row[2] or "warning"
                        alertname = alertname_part
                    else:
                        history_id = None
                        feishu_open_message_id = None
                else:
                    logger.warning(
                        f"无效的alert_id格式: {alert_id}",
                        extra={"action": "feishu.callback", "alert_id": alert_id},
                    )
                    history_id = None
                    feishu_open_message_id = None
                    alertname, instance, severity = "", "", "warning"

            if history_id:
                conn.execute(
                    text("UPDATE alert_history SET status = 'resolved' WHERE id = :id"),
                    {"id": history_id},
                )
                conn.commit()
                logger.info(
                    f"告警 {alert_id} 已解决",
                    extra={"action": "feishu.callback", "alert_id": alert_id, "notes": notes},
                )

                if feishu_open_message_id:
                    feishu_svc = get_feishu_notification_service()
                    resolved_card = feishu_svc.build_resolved_card(
                        alertname=alertname,
                        severity=severity,
                        instance=instance,
                    )
                    feishu_svc.update_card_message(
                        open_message_id=feishu_open_message_id,
                        card_content=resolved_card,
                    )
            else:
                logger.warning(
                    f"未找到firing状态的告警: {alert_id}",
                    extra={"action": "feishu.callback", "alert_id": alert_id},
                )
        engine.dispose()
    except Exception as e:
        logger.error(
            f"解决告警失败: {alert_id}",
            extra={"action": "feishu.callback", "alert_id": alert_id, "error": str(e)},
        )


def _start_callback_client() -> None:
    """Start the Feishu WebSocket callback client."""
    global _ws_client

    if not settings.feishu_enable or not settings.feishu_app_id or not settings.feishu_app_secret:
        logger.warning("飞书集成未启用，跳过回调客户端", extra={"action": "feishu.callback"})
        return

    lark = _get_lark_module()

    logger.info(
        f"初始化飞书WebSocket客户端: app_id={settings.feishu_app_id[:8]}...",
        extra={"action": "feishu.callback"},
    )

    event_handler = (
        lark.EventDispatcherHandler.builder("", "")
        .register_p2_card_action_trigger(_do_card_action_trigger)
        .register_p2_im_message_receive_v1(_do_im_message_receive_v1)
        .register_p2_im_chat_access_event_bot_p2p_chat_entered_v1(_do_bot_p2p_chat_entered)
        .register_p2_im_message_reaction_created_v1(_do_im_message_reaction_created_v1)
        .register_p2_im_message_message_read_v1(_do_im_message_message_read_v1)
        .build()
    )

    logger.info("事件处理器已注册，创建WebSocket客户端", extra={"action": "feishu.callback"})

    _ws_client = lark.ws.Client(
        settings.feishu_app_id,
        settings.feishu_app_secret,
        event_handler=event_handler,
        log_level=lark.LogLevel.WARNING,
    )

    logger.info("WebSocket客户端已创建，开始连接", extra={"action": "feishu.callback"})
    try:
        _ws_client.start()
        logger.info("WebSocket客户端已启动", extra={"action": "feishu.callback"})
    except Exception as e:
        logger.error(
            f"WebSocket客户端启动失败: {type(e).__name__}: {e}",
            extra={"action": "feishu.callback", "error": str(e), "error_type": type(e).__name__},
            exc_info=True,
        )


def start_feishu_callback_client() -> None:
    """Start the Feishu callback client in a background thread."""
    global _callback_thread

    if _callback_thread is not None and _callback_thread.is_alive():
        logger.info("飞书回调客户端已在运行", extra={"action": "feishu.callback"})
        return

    _callback_thread = threading.Thread(target=_start_callback_client, daemon=True)
    _callback_thread.start()
    logger.info("飞书回调客户端已在后台线程启动", extra={"action": "feishu.callback"})


def stop_feishu_callback_client() -> None:
    """Stop the Feishu callback client."""
    global _ws_client
    if _ws_client:
        _ws_client.stop()
        logger.info("飞书WebSocket客户端已停止", extra={"action": "feishu.callback"})


def _do_bot_p2p_chat_entered(data: Any) -> None:
    """Handle bot entered p2p chat event."""
    lark = _get_lark_module()
    logger.info(f"机器人进入单聊: {lark.JSON.marshal(data)}", extra={"action": "feishu.callback"})

    try:
        open_id = None
        if hasattr(data.event, "operator") and data.event.operator:
            operator_id = getattr(data.event.operator, "operator_id", None)
            if operator_id:
                open_id = getattr(operator_id, "open_id", None)
        _record_interaction(
            direction="inbound",
            interaction_type="chat_entered",
            feishu_open_id=open_id,
        )
    except Exception as e:
        logger.error(
            f"记录chat_entered交互失败: {e}", extra={"action": "feishu.callback", "error": str(e)}
        )

    return None


def _do_im_message_reaction_created_v1(data: Any) -> None:
    """Handle im.message.reaction.created_v1 event."""
    lark = _get_lark_module()

    # 过滤应用自身触发的表情回应事件
    operator_type = getattr(data.event, "operator_type", None)
    if operator_type == "app":
        logger.debug(
            "跳过应用自身触发的表情回应事件",
            extra={"action": "feishu.callback", "operator_type": operator_type},
        )
        return None

    logger.info(f"表情回应创建: {lark.JSON.marshal(data)}", extra={"action": "feishu.callback"})

    try:
        open_id = None
        emoji_type = None
        message_id = None
        if hasattr(data.event, "operator") and data.event.operator:
            operator_id = getattr(data.event.operator, "operator_id", None)
            if operator_id:
                open_id = getattr(operator_id, "open_id", None)
        reaction = getattr(data.event, "reaction", None)
        if reaction:
            emoji = getattr(reaction, "emoji", None)
            if emoji:
                emoji_type = getattr(emoji, "emoji_type", None)
            message_id = getattr(reaction, "message_id", None)
        _record_interaction(
            direction="inbound",
            interaction_type="reaction",
            feishu_open_id=open_id,
            message_id=message_id,
            content={"emoji_type": emoji_type},
        )
    except Exception as e:
        logger.error(
            f"记录reaction交互失败: {e}", extra={"action": "feishu.callback", "error": str(e)}
        )

    return None


def _do_im_message_message_read_v1(data: Any) -> None:
    """Handle im.message.message_read_v1 event."""
    lark = _get_lark_module()
    logger.info(f"消息已读事件: {lark.JSON.marshal(data)}", extra={"action": "feishu.callback"})

    try:
        open_id = None
        message_id_list = None
        reader = getattr(data.event, "reader", None)
        if reader:
            reader_id = getattr(reader, "reader_id", None)
            if reader_id:
                open_id = getattr(reader_id, "open_id", None)
            message_id_list = getattr(reader, "message_id_list", None)
        _record_interaction(
            direction="inbound",
            interaction_type="message_read",
            feishu_open_id=open_id,
            content={"message_id_list": message_id_list},
        )
    except Exception as e:
        logger.error(
            f"记录message_read交互失败: {e}", extra={"action": "feishu.callback", "error": str(e)}
        )

    return None


def _do_im_message_receive_v1(data: Any) -> Any:
    """Handle im.message.receive_v1 event - receive user messages."""
    try:
        lark = _get_lark_module()
        message_content = lark.JSON.marshal(data)
        logger.info(
            "收到消息", extra={"action": "feishu.callback", "message_data": message_content}
        )

        event = data.event
        sender = getattr(event, "sender", None)
        sender_id = None
        if sender:
            sender_id = getattr(sender, "sender_id", None)
            if sender_id:
                sender_id = getattr(sender_id, "open_id", None) or getattr(
                    sender_id, "user_id", None
                )

        message = getattr(event, "message", None)
        message_id = getattr(message, "message_id", None) if message else None
        chat_type = getattr(message, "chat_type", None) if message else None

        # 仅当消息指向该应用时才回复表情：单聊直接回复，群聊需被 @
        should_salute = chat_type == "p2p"
        if not should_salute and chat_type == "group":
            mentions = getattr(message, "mentions", None) if message else None
            if mentions:
                for mention in mentions:
                    mention_id = getattr(mention, "id", None)
                    if mention_id:
                        # 飞书 SDK Mention.id 不含 app_id，机器人被 @时 user_id 为空
                        mention_app_id = getattr(mention_id, "app_id", None)
                        mention_user_id = getattr(mention_id, "user_id", None)
                        if mention_app_id == settings.feishu_app_id or not mention_user_id:
                            should_salute = True
                            break

        content = getattr(message, "content", None) if message else None
        # 注意：msg_type 必须从 message.message_type 获取，
        # 不能从 content JSON 中解析（content 只有 {"text":"..."}，不含 msg_type 字段）
        msg_type = getattr(message, "message_type", "") if message else ""
        text_content = ""
        if content:
            try:
                msg_dict = json.loads(content) if isinstance(content, str) else content
                text_content = msg_dict.get("text", "") if isinstance(msg_dict, dict) else ""

                logger.info(
                    f"消息来自 {sender_id}: type={msg_type}",
                    extra={
                        "action": "feishu.callback",
                        "sender_id": sender_id,
                        "msg_type": msg_type,
                        "text_content": text_content,
                    },
                )

                _record_interaction(
                    direction="inbound",
                    interaction_type="message",
                    feishu_open_id=sender_id,
                    message_id=message_id,
                    content={"msg_type": msg_type, "text": text_content},
                    msg_type=msg_type,
                )

                if msg_type == "text" and text_content:
                    _handle_text_message(sender_id, text_content)
            except Exception as e:
                logger.error(
                    f"解析消息内容失败: {e}", extra={"action": "feishu.callback", "error": str(e)}
                )

        if message_id and should_salute:
            _send_salute_reaction(message_id)
        return None

    except Exception as e:
        logger.error(f"处理消息失败: {e}", extra={"action": "feishu.callback", "error": str(e)})
        return None


def _send_salute_reaction(message_id: str | None) -> None:
    """Add salute emoji reaction to the message."""
    if not message_id:
        return
    try:
        from app.integrations.feishu.service import get_feishu_service

        feishu = get_feishu_service()
        feishu.add_message_reaction(message_id, emoji_type="Typing")
        logger.info(
            f"已添加表情回应: message_id={message_id}",
            extra={"action": "feishu.callback", "message_id": message_id},
        )
    except Exception as e:
        logger.error(f"添加表情回应失败: {e}", extra={"action": "feishu.callback", "error": str(e)})


def _handle_text_message(sender_id: str | None, text: str) -> None:
    """Handle incoming text messages."""
    if not sender_id:
        return

    # 归一化：去除首尾空白并转小写；再做去空格匹配，兼容 "CRM 增量同步"/"CRM增量同步"
    text_lower = text.strip().lower()
    text_normalized = text_lower.replace(" ", "")

    # CRM 同步触发：接收文本消息 "CRM 增量同步" / "CRM 全量同步"
    crm_sync_type: str | None = None
    if text_normalized == "crm增量同步":
        crm_sync_type = "incremental"
    elif text_normalized == "crm全量同步":
        crm_sync_type = "full"

    if crm_sync_type:
        _trigger_crm_sync_from_text(sender_id, crm_sync_type)
        return

    if text_lower in ["help", "帮助", "菜单"]:
        _send_help_menu(sender_id)
    elif text_lower in ["状态", "status"]:
        _send_status_info(sender_id)
    else:
        logger.info(
            f"收到文本消息: sender_id={sender_id}, text={text_lower}",
            extra={"action": "feishu.callback", "sender_id": sender_id},
        )


def _trigger_crm_sync_from_text(sender_id: str, sync_type: str) -> None:
    """从文本消息触发 CRM 同步。

    流程：
    1. 检查是否已在同步中（去重），若在同步中则静默忽略，不发送任何消息
    2. 立即回复用户"正在执行..."的文本消息
    3. 启动后台线程执行同步调用并发送结果卡片

    Args:
        sender_id: 触发同步的用户 open_id
        sync_type: 同步类型 "incremental" 或 "full"
    """
    from app.services.crm.sync_service import SYNC_TYPE_LABELS

    label = SYNC_TYPE_LABELS.get(sync_type, sync_type)

    logger.info(
        f"[CRM文本触发] 收到文本指令: sender_id={sender_id}, sync_type={sync_type}, label={label}",
        extra={
            "action": "crm.sync.text_trigger",
            "sender_id": sender_id,
            "sync_type": sync_type,
            "label": label,
        },
    )

    # 0. 去重检查：若该 sync_type 已在同步中，忽略重复指令（不发送任何消息）
    with _crm_sync_in_progress_lock:
        if _crm_sync_in_progress.get(sync_type):
            logger.info(
                f"[CRM文本触发] 同步进行中，忽略重复指令: sender_id={sender_id}, sync_type={sync_type}",
                extra={
                    "action": "crm.sync.text_trigger",
                    "sender_id": sender_id,
                    "sync_type": sync_type,
                    "step": "duplicate_ignored",
                },
            )
            return
        # 标记为同步中
        _crm_sync_in_progress[sync_type] = True

    # 1. 立即回复文本消息，告知用户已收到指令
    try:
        from app.integrations.feishu.service import get_feishu_service

        feishu = get_feishu_service()
        feishu.send_text_message(sender_id, f"⏳ 已收到指令，正在执行 {label}，请稍候...")
        logger.info(
            f"[CRM文本触发] 已回复执行中提示: sender_id={sender_id}",
            extra={"action": "crm.sync.text_trigger", "sender_id": sender_id, "step": "reply_running"},
        )
    except Exception as e:
        logger.error(
            f"[CRM文本触发] 回复执行中提示失败: {e}",
            extra={"action": "crm.sync.text_trigger", "sender_id": sender_id, "error": str(e), "step": "reply_running_error"},
        )

    # 2. 启动后台线程执行同步并发送结果卡片
    threading.Thread(
        target=_run_crm_sync_from_text,
        args=(sender_id, sync_type),
        daemon=True,
    ).start()


def _run_crm_sync_from_text(sender_id: str, sync_type: str) -> None:
    """在后台线程中执行 CRM 同步，并更新卡片状态。

    流程（卡片更新模式，而非新下发）：
    1. 发送"同步中"卡片，记录 message_id
    2. 调用 CRM 同步接口，获取 task_id 和 status_url
    3. 如果触发成功且有 status_url：
       - 等待指定时间（增量 5 分钟，全量 15 分钟）
       - 查询同步状态
       - 更新原卡片为最终结果
    4. 如果触发失败，立即更新原卡片为失败状态

    所有异常都在顶层捕获并记录，避免线程静默失败。
    无论同步成功失败，最终都会清除同步状态，允许下一次触发。
    """
    import time

    label = sync_type
    card_message_id: str | None = None
    try:
        from app.services.crm.card_updater import (
            send_syncing_card_sync,
            update_card_to_sync_result_sync,
        )
        from app.services.crm.sync_service import (
            SYNC_TYPE_LABELS,
            SYNC_WAIT_SECONDS,
            get_crm_sync_service,
        )

        label = SYNC_TYPE_LABELS.get(sync_type, sync_type)
        wait_seconds = SYNC_WAIT_SECONDS.get(sync_type, 300)
        logger.info(
            f"[CRM文本触发] 开始执行同步: sender_id={sender_id}, sync_type={sync_type}, wait_seconds={wait_seconds}",
            extra={
                "action": "crm.sync.text_trigger",
                "sender_id": sender_id,
                "sync_type": sync_type,
                "wait_seconds": wait_seconds,
                "step": "start",
            },
        )

        # 1. 发送"同步中"卡片，记录 message_id 用于后续更新
        try:
            card_message_id = send_syncing_card_sync(sender_id, sync_type)
            logger.info(
                f"[CRM文本触发] 已发送同步中卡片: sender_id={sender_id}, card_message_id={card_message_id}",
                extra={"action": "crm.sync.text_trigger", "sender_id": sender_id, "card_message_id": card_message_id, "step": "send_syncing_card_done"},
            )
        except Exception as e:
            logger.warning(
                f"[CRM文本触发] 发送同步中卡片失败: {e}",
                extra={"action": "crm.sync.text_trigger", "sender_id": sender_id, "error": str(e), "step": "send_syncing_card_error"},
            )

        # 2. 调用 CRM 同步接口
        service = get_crm_sync_service()
        url = service._build_url(sync_type)
        logger.info(
            f"[CRM文本触发] 调用 CRM 接口: url={url}",
            extra={"action": "crm.sync.text_trigger", "url": url, "sync_type": sync_type, "step": "call_crm_api"},
        )

        trigger_result = service.trigger_sync_sync(sync_type)
        logger.info(
            f"[CRM文本触发] CRM 接口调用完成: success={trigger_result.get('success')}, status_code={trigger_result.get('status_code')}, duration_ms={trigger_result.get('duration_ms')}",
            extra={
                "action": "crm.sync.text_trigger",
                "sync_type": sync_type,
                "success": trigger_result.get("success"),
                "status_code": trigger_result.get("status_code"),
                "duration_ms": trigger_result.get("duration_ms"),
                "step": "call_crm_api_done",
            },
        )

        # 3. 判断是否需要等待查询状态
        trigger_data = trigger_result.get("data") or {}
        status_url = trigger_data.get("status_url") if isinstance(trigger_data, dict) else None

        if not trigger_result.get("success") or not status_url:
            # 触发失败，立即更新卡片为失败状态
            logger.info(
                f"[CRM文本触发] 触发失败或无 status_url，立即更新卡片为失败状态: success={trigger_result.get('success')}, has_status_url={bool(status_url)}",
                extra={"action": "crm.sync.text_trigger", "success": trigger_result.get("success"), "has_status_url": bool(status_url), "step": "update_card_failed_immediately"},
            )
            _update_crm_sync_card(sender_id, card_message_id, sync_type, trigger_result)
            logger.info(
                f"[CRM文本触发] {label} 全流程完成（触发失败）: success=False",
                extra={"action": "crm.sync.text_trigger", "sync_type": sync_type, "success": False, "sender_id": sender_id, "step": "all_done_failed"},
            )
            return

        # 4. 触发成功，等待指定时间后查询状态
        logger.info(
            f"[CRM文本触发] 触发成功，等待 {wait_seconds}s 后查询同步状态: task_id={trigger_data.get('task_id')}, status_url={status_url}",
            extra={
                "action": "crm.sync.text_trigger",
                "sync_type": sync_type,
                "wait_seconds": wait_seconds,
                "task_id": trigger_data.get("task_id"),
                "status_url": status_url,
                "step": "wait_before_query",
            },
        )
        time.sleep(wait_seconds)

        # 5. 查询同步状态
        query_result = service.query_sync_status_sync(status_url)
        logger.info(
            f"[CRM文本触发] 同步状态查询完成: success={query_result.get('success')}, status_code={query_result.get('status_code')}",
            extra={
                "action": "crm.sync.text_trigger",
                "sync_type": sync_type,
                "query_success": query_result.get("success"),
                "status_code": query_result.get("status_code"),
                "step": "query_status_done",
            },
        )

        # 6. 构建最终结果并更新卡片
        final_result = _build_final_sync_result(sync_type, trigger_result, query_result)
        _update_crm_sync_card(sender_id, card_message_id, sync_type, final_result)

        logger.info(
            f"[CRM文本触发] {label} 全流程完成: success={final_result.get('success')}",
            extra={
                "action": "crm.sync.text_trigger",
                "sync_type": sync_type,
                "success": final_result.get("success"),
                "sender_id": sender_id,
                "step": "all_done",
            },
        )

    except Exception as e:
        logger.error(
            f"[CRM文本触发] {label} 执行异常（顶层捕获）: {e}",
            extra={
                "action": "crm.sync.text_trigger",
                "sync_type": sync_type,
                "sender_id": sender_id,
                "error": str(e),
                "error_type": type(e).__name__,
                "step": "top_level_error",
            },
            exc_info=True,
        )
        # 异常时尝试更新卡片为失败状态
        if card_message_id:
            try:
                from app.services.crm.card_updater import update_card_to_sync_result_sync

                error_result = {
                    "success": False,
                    "message": f"{label} 执行异常: {str(e)}",
                    "error": str(e),
                    "started_at": "",
                    "duration_ms": 0,
                }
                update_card_to_sync_result_sync(card_message_id, sync_type, error_result)
            except Exception:
                pass
    finally:
        # 无论成功失败，清除同步状态，允许下一次触发
        with _crm_sync_in_progress_lock:
            _crm_sync_in_progress[sync_type] = False
        logger.info(
            f"[CRM文本触发] 已清除同步状态: sync_type={sync_type}",
            extra={"action": "crm.sync.text_trigger", "sync_type": sync_type, "step": "clear_in_progress"},
        )


def _update_crm_sync_card(
    sender_id: str,
    card_message_id: str | None,
    sync_type: str,
    result: dict,
) -> None:
    """更新 CRM 同步卡片为最终结果。

    优先使用 update_card_message 更新原卡片；
    若 card_message_id 为空（发送同步中卡片失败），则降级为发送新卡片。
    """
    from app.services.crm.card_updater import (
        send_sync_result_card_sync,
        update_card_to_sync_result_sync,
    )

    if card_message_id:
        try:
            update_card_to_sync_result_sync(card_message_id, sync_type, result)
            logger.info(
                f"[CRM文本触发] 已更新卡片为最终结果: card_message_id={card_message_id}",
                extra={"action": "crm.sync.text_trigger", "card_message_id": card_message_id, "step": "update_card_result_done"},
            )
            return
        except Exception as e:
            logger.warning(
                f"[CRM文本触发] 更新卡片失败，降级为发送新卡片: {e}",
                extra={"action": "crm.sync.text_trigger", "card_message_id": card_message_id, "error": str(e), "step": "update_card_fallback"},
            )

    # 降级：发送新卡片
    try:
        send_sync_result_card_sync(sender_id, sync_type, result)
        logger.info(
            f"[CRM文本触发] 已发送结果卡片（降级）: sender_id={sender_id}",
            extra={"action": "crm.sync.text_trigger", "sender_id": sender_id, "step": "send_result_card_fallback_done"},
        )
    except Exception as e:
        logger.error(
            f"[CRM文本触发] 发送结果卡片（降级）失败: {e}",
            extra={"action": "crm.sync.text_trigger", "sender_id": sender_id, "error": str(e), "step": "send_result_card_fallback_error"},
        )


def _build_final_sync_result(
    sync_type: str,
    trigger_result: dict,
    query_result: dict,
) -> dict:
    """根据触发结果和状态查询结果，构建用于更新卡片的最终结果。

    判断同步是否完成的规则：
    - 查询成功且返回数据中 status 字段为 completed/success/done 视为成功
    - 否则视为未完成（但仍更新卡片显示当前状态）
    """
    from app.services.crm.sync_service import SYNC_TYPE_LABELS

    label = SYNC_TYPE_LABELS.get(sync_type, sync_type)
    trigger_data = trigger_result.get("data") or {}
    query_data = query_result.get("data") or {}

    # 判断同步任务状态
    task_status = ""
    if isinstance(query_data, dict):
        task_status = str(query_data.get("status", "")).lower()

    # 视为成功的状态值
    success_statuses = {"completed", "success", "done", "finished", "succeeded"}
    is_success = query_result.get("success", False) and (
        task_status in success_statuses or not task_status
    )

    # 合并数据用于卡片展示
    combined_data = {
        "trigger": trigger_data,
        "query": query_data,
    }

    if is_success:
        message = f"{label} 已完成"
    else:
        message = f"{label} 状态查询完成（当前状态: {task_status or 'unknown'}）"

    return {
        "success": is_success,
        "message": message,
        "sync_type": sync_type,
        "label": label,
        "started_at": trigger_result.get("started_at", ""),
        "duration_ms": trigger_result.get("duration_ms", 0),
        "status_code": query_result.get("status_code", ""),
        "data": combined_data,
        "error": query_result.get("error", "") if not is_success else "",
    }


def _send_help_menu(user_id: str) -> None:
    """Send help menu to user."""
    try:
        from app.integrations.feishu.service import get_feishu_service

        feishu = get_feishu_service()
        card_content = {
            "schema": "2.0",
            "header": {
                "title": {"tag": "plain_text", "content": "IT反馈机器人帮助"},
                "template": "blue",
            },
            "body": {
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": "**欢迎使用IT反馈机器人**\n\n请选择操作：",
                        },
                    },
                    {
                        "tag": "column_set",
                        "flex_mode": "center",
                        "columns": [
                            {
                                "tag": "column",
                                "width": "weighted",
                                "weight": 1,
                                "elements": [
                                    {
                                        "tag": "button",
                                        "text": {"tag": "plain_text", "content": "提交反馈"},
                                        "type": "primary",
                                        "width": "fill",
                                        "behaviors": [
                                            {
                                                "type": "callback",
                                                "value": {"action": "submit_feedback"},
                                            }
                                        ],
                                    }
                                ],
                            },
                            {
                                "tag": "column",
                                "width": "weighted",
                                "weight": 1,
                                "elements": [
                                    {
                                        "tag": "button",
                                        "text": {"tag": "plain_text", "content": "查看状态"},
                                        "type": "default",
                                        "width": "fill",
                                        "behaviors": [
                                            {
                                                "type": "callback",
                                                "value": {"action": "check_status"},
                                            }
                                        ],
                                    }
                                ],
                            },
                        ],
                    },
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": "---\n**使用说明**\n- 发送 `状态` 查看当前反馈状态\n- 发送 `帮助` 显示此菜单",
                        },
                    },
                ],
            },
        }
        feishu.send_p2p_card_message(user_id, card_content)
    except Exception as e:
        logger.error(f"发送帮助菜单失败: {e}", extra={"action": "feishu.callback", "error": str(e)})


def _send_status_info(user_id: str) -> None:
    """Send status info to user."""
    try:
        from app.integrations.feishu.service import get_feishu_service

        feishu = get_feishu_service()
        card_content = {
            "header": {
                "title": {"tag": "plain_text", "content": "IT反馈状态查询"},
                "template": "green",
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {"tag": "lark_md", "content": "请通过工单系统查询您的反馈状态"},
                },
                {"tag": "div", "text": {"tag": "lark_md", "content": "或联系IT管理员获取帮助"}},
            ],
        }
        feishu.send_p2p_card_message(user_id, card_content)
    except Exception as e:
        logger.error(f"发送状态信息失败: {e}", extra={"action": "feishu.callback", "error": str(e)})
