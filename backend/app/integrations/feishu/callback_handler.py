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


def _try_forward_callback(
    open_message_id: str | None,
    data: Any,
    button_action: str,
    value: dict | str,
    operator_open_id: str | None,
) -> None:
    if not open_message_id:
        return

    try:
        from app.db.session import SessionLocal
        from app.models.notification_record import NotificationRecord
        from app.crud.crud_notification_callback_log import notification_callback_log
        from sqlalchemy import select

        with SessionLocal() as db:
            result = db.execute(
                select(NotificationRecord).where(
                    NotificationRecord.open_message_id == open_message_id,
                    NotificationRecord.callback_url.isnot(None),
                )
            )
            record = result.scalar_one_or_none()

        if not record or not record.callback_url:
            return

        callback_url = record.callback_url

        operator_info = {}
        if hasattr(data.event, "operator") and data.event.operator:
            op = data.event.operator
            operator_info = {
                "open_id": getattr(op, "open_id", None) or (getattr(getattr(op, "operator_id", None), "open_id", None)),
                "user_id": getattr(op, "user_id", None) or (getattr(getattr(op, "operator_id", None), "user_id", None)),
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
            "timestamp": __import__("datetime").datetime.now(
                tz=__import__("datetime").timezone.utc
            ).isoformat(),
        }

        import httpx

        with httpx.Client(timeout=5.0) as client:
            response = client.post(callback_url, json=callback_data)

        with SessionLocal() as db:
            notification_callback_log.create(
                db,
                notification_record_id=record.id,
                callback_url=callback_url,
                request_body=callback_data,
                response_status=response.status_code,
                response_body=response.text[:2000],
                status="success",
            )

        logger.info(
            f"回调转发成功: {callback_url}",
            extra={"action": "feishu.callback.forward", "callback_url": callback_url, "status_code": response.status_code},
        )

    except Exception as e:
        logger.warning(
            f"回调转发失败: {e}",
            extra={"action": "feishu.callback.forward", "error": str(e), "open_message_id": open_message_id},
        )
        try:
            from app.db.session import SessionLocal
            from app.crud.crud_notification_callback_log import notification_callback_log

            with SessionLocal() as db:
                notification_callback_log.create(
                    db,
                    notification_record_id=record.id if "record" in dir() else None,
                    callback_url=callback_url if "callback_url" in dir() else "",
                    request_body=callback_data if "callback_data" in dir() else None,
                    status="failed",
                    error_message=str(e),
                )
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
    action_tag = getattr(data.event.action, "tag", None) if hasattr(data, "event") and hasattr(data.event, "action") else None
    logger.info(f"收到卡片回调: action={action_tag}", extra={"action": "feishu.callback", "callback_data": data_str})

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

        _record_interaction(
            direction="inbound",
            interaction_type="card_action",
            feishu_open_id=operator_open_id,
            message_id=open_message_id,
            content={"action": button_action, "value": value if isinstance(value, dict) else str(value)},
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

            logger.info(f"完成反馈处理: {feedback_id}", extra={"action": "feishu.callback", "feedback_id": feedback_id, "notes": notes})

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
            logger.info(f"反馈 {feedback_id} 标记为处理中", extra={"action": "feishu.callback", "feedback_id": feedback_id})
        engine.dispose()
    except Exception as e:
        logger.error(f"处理反馈失败: {feedback_id}", extra={"action": "feishu.callback", "feedback_id": feedback_id, "error": str(e)})


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
        logger.error(f"通过open_message_id查询feedback_id失败: {open_message_id}", extra={"action": "feishu.callback", "open_message_id": open_message_id, "error": str(e)})
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
            logger.info(f"反馈 {feedback_id} 已解决", extra={"action": "feishu.callback", "feedback_id": feedback_id, "notes": notes})
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
                    extra={"action": "feishu.callback", "feishu_open_id": feishu_open_id, "feedback_id": feedback_id},
                )
            except Exception as e:
                logger.error(f"发送通知失败: {e}", extra={"action": "feishu.callback", "error": str(e)})
        else:
            logger.warning(
                f"未找到飞书open_id: customer={customer}, 跳过通知", extra={"action": "feishu.callback", "customer": customer}
            )

    except Exception as e:
        logger.error(f"完成反馈失败: {feedback_id}", extra={"action": "feishu.callback", "feedback_id": feedback_id, "error": str(e)})


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
            logger.info(f"反馈 {feedback_id} 标记为已解决", extra={"action": "feishu.callback", "feedback_id": feedback_id})
        engine.dispose()
    except Exception as e:
        logger.error(f"解决反馈失败: {feedback_id}", extra={"action": "feishu.callback", "feedback_id": feedback_id, "error": str(e)})


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
        logger.error(f"更新卡片为处理中状态失败: {e}", extra={"action": "feishu.callback", "error": str(e)})


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
        logger.error(f"更新卡片为已解决状态失败: {e}", extra={"action": "feishu.callback", "error": str(e)})


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
        logger.error(f"通过open_message_id查询alert_id失败: {open_message_id}", extra={"action": "feishu.callback", "open_message_id": open_message_id, "error": str(e)})
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
            logger.info(f"告警卡片 {alert_id} 已更新为接单状态", extra={"action": "feishu.callback", "alert_id": alert_id})
    except Exception as e:
        logger.error(f"接单失败: {alert_id}", extra={"action": "feishu.callback", "alert_id": alert_id, "error": str(e)})


def _send_transfer_notification(alert_id: str, alertname: str, severity: str, instance: str) -> None:
    """Send notification to IT team members when alert is transferred."""
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import selectinload

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
                {"notif_type": NOTIFICATION_TYPE_ALERT_TRANSFERRED_TO_IT}
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
            logger.info(f"转交通知已发送: user_id={user_id}, message_id={result.get('message_id')}", extra={"action": "feishu.callback", "user_id": user_id})
        else:
            logger.warning(f"转交通知发送失败: {user_id}", extra={"action": "feishu.callback", "user_id": user_id})
    except Exception as e:
        logger.error(f"发送转交卡片失败: {user_id}", extra={"action": "feishu.callback", "user_id": user_id, "error": str(e)})


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
            logger.info(f"告警卡片 {alert_id} 已更新为转交状态", extra={"action": "feishu.callback", "alert_id": alert_id})

        _send_transfer_notification(alert_id, alertname, severity, instance)
    except Exception as e:
        logger.error(f"转交告警失败: {alert_id}", extra={"action": "feishu.callback", "alert_id": alert_id, "error": str(e)})


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
                    logger.warning(f"无效的alert_id格式: {alert_id}", extra={"action": "feishu.callback", "alert_id": alert_id})
                    history_id = None
                    feishu_open_message_id = None
                    alertname, instance, severity = "", "", "warning"

            if history_id:
                conn.execute(
                    text("UPDATE alert_history SET status = 'resolved' WHERE id = :id"),
                    {"id": history_id},
                )
                conn.commit()
                logger.info(f"告警 {alert_id} 已解决", extra={"action": "feishu.callback", "alert_id": alert_id, "notes": notes})

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
                logger.warning(f"未找到firing状态的告警: {alert_id}", extra={"action": "feishu.callback", "alert_id": alert_id})
        engine.dispose()
    except Exception as e:
        logger.error(f"解决告警失败: {alert_id}", extra={"action": "feishu.callback", "alert_id": alert_id, "error": str(e)})


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
    except RuntimeError:
        logger.warning(
            "WebSocket客户端无法启动（事件循环冲突），"
            "uvicorn reload模式下会出现此问题，"
            "生产环境请使用 'uvicorn app.main:app' 不带 --reload",
            extra={"action": "feishu.callback"},
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
        logger.error(f"记录chat_entered交互失败: {e}", extra={"action": "feishu.callback", "error": str(e)})

    return None


def _do_im_message_reaction_created_v1(data: Any) -> None:
    """Handle im.message.reaction.created_v1 event."""
    lark = _get_lark_module()
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
        logger.error(f"记录reaction交互失败: {e}", extra={"action": "feishu.callback", "error": str(e)})

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
        logger.error(f"记录message_read交互失败: {e}", extra={"action": "feishu.callback", "error": str(e)})

    return None


def _do_im_message_receive_v1(data: Any) -> Any:
    """Handle im.message.receive_v1 event - receive user messages."""
    try:
        lark = _get_lark_module()
        message_content = lark.JSON.marshal(data)
        logger.info("收到消息", extra={"action": "feishu.callback", "message_data": message_content})

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

        content = getattr(message, "content", None) if message else None
        msg_type = ""
        text_content = ""
        if content:
            try:
                msg_dict = json.loads(content) if isinstance(content, str) else content
                msg_type = msg_dict.get("msg_type", "") if isinstance(msg_dict, dict) else ""
                text_content = msg_dict.get("text", "") if isinstance(msg_dict, dict) else ""

                logger.info(
                    f"消息来自 {sender_id}: type={msg_type}",
                    extra={"action": "feishu.callback", "sender_id": sender_id, "msg_type": msg_type, "text_content": text_content},
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
                logger.error(f"解析消息内容失败: {e}", extra={"action": "feishu.callback", "error": str(e)})

        if message_id:
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
        logger.info(f"已添加表情回应: message_id={message_id}", extra={"action": "feishu.callback", "message_id": message_id})
    except Exception as e:
        logger.error(f"添加表情回应失败: {e}", extra={"action": "feishu.callback", "error": str(e)})


def _handle_text_message(sender_id: str | None, text: str) -> None:
    """Handle incoming text messages."""
    if not sender_id:
        return

    text = text.strip().lower()

    if text in ["help", "帮助", "菜单"]:
        _send_help_menu(sender_id)
    elif text in ["状态", "status"]:
        _send_status_info(sender_id)
    else:
        logger.info(f"收到文本消息: sender_id={sender_id}, text={text}", extra={"action": "feishu.callback", "sender_id": sender_id})


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
                                        "behaviors": [{"type": "callback", "value": {"action": "submit_feedback"}}],
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
                                        "behaviors": [{"type": "callback", "value": {"action": "check_status"}}],
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
