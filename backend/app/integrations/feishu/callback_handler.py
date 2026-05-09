"""
Feishu callback handler for long connection (WebSocket) mode.
"""

import json
import logging
import threading
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

NOTIFICATION_TYPE_ALERT_TRANSFERRED_TO_IT = "alert_transferred_to_it"

_lark = None
_callback_thread: threading.Thread | None = None
_ws_client: Any = None


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
    logger.info(f"Card callback received: {data_str[:200]}...")

    try:
        action = data.event.action
        action_tag = getattr(action, "tag", None)
        value = action.value if hasattr(action, "value") and action.value else {}
        form_value = getattr(action, "form_value", None)
        input_value = getattr(action, "input_value", None)
        name = getattr(action, "name", None)

        if action_tag == "input":
            logger.info("Ignoring input tag callback, waiting for form submission")
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

            logger.info(f"Finish feedback {feedback_id}, notes: '{notes}'")

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
            resp = {"toast": {"type": "info", "content": f"收到回调: {button_action}"}}

        from lark_oapi.event.callback.model.p2_card_action_trigger import (
            P2CardActionTriggerResponse,
        )

        return P2CardActionTriggerResponse(resp)

    except Exception as e:
        logger.error(f"Error processing card action: {e}")
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
            logger.info(f"Feedback {feedback_id} marked as handling")
        engine.dispose()
    except Exception as e:
        logger.error(f"Error handling feedback {feedback_id}: {e}")


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
        logger.error(f"Error getting feedback_id by open_message_id {open_message_id}: {e}")
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
            logger.info(f"Feedback {feedback_id} marked as resolved with notes: {notes}")
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
                    f"Notification sent to feishu_open_id {feishu_open_id} (customer: {customer}) for feedback {feedback_id}"
                )
            except Exception as e:
                logger.error(f"Failed to send notification: {e}")
        else:
            logger.warning(
                f"No feishu_open_id found for customer {customer}, skipping notification"
            )

    except Exception as e:
        logger.error(f"Error finishing feedback {feedback_id}: {e}")


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
            logger.info(f"Feedback {feedback_id} marked as resolved")
        engine.dispose()
    except Exception as e:
        logger.error(f"Error resolving feedback {feedback_id}: {e}")


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
        logger.error(f"Error updating card to handling: {e}")


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
        logger.error(f"Error updating card to resolved: {e}")


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
        logger.error(f"Error getting alert_id by open_message_id {open_message_id}: {e}")
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
            logger.info(f"Alert card {alert_id} updated to acknowledged status")
    except Exception as e:
        logger.error(f"Error acknowledging alert {alert_id}: {e}")


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
        logger.error(f"Error sending transfer notification: {e}")


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
            logger.info(f"Transfer notification sent to {user_id}, message_id={result.get('message_id')}")
        else:
            logger.warning(f"Failed to send transfer notification to {user_id}")
    except Exception as e:
        logger.error(f"Error sending transfer card to {user_id}: {e}")


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
            logger.info(f"Alert card {alert_id} updated to transferred status")

        _send_transfer_notification(alert_id, alertname, severity, instance)
    except Exception as e:
        logger.error(f"Error transferring alert {alert_id} to IT: {e}")


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
                    logger.warning(f"Invalid alert_id format: {alert_id}")
                    history_id = None
                    feishu_open_message_id = None
                    alertname, instance, severity = "", "", "warning"

            if history_id:
                conn.execute(
                    text("UPDATE alert_history SET status = 'resolved' WHERE id = :id"),
                    {"id": history_id},
                )
                conn.commit()
                logger.info(f"Alert {alert_id} marked as resolved with notes: {notes}")

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
                logger.warning(f"No firing alert found for: {alert_id}")
        engine.dispose()
    except Exception as e:
        logger.error(f"Error resolving alert {alert_id}: {e}")


def _start_callback_client() -> None:
    """Start the Feishu WebSocket callback client."""
    global _ws_client

    if not settings.feishu_enable or not settings.feishu_app_id or not settings.feishu_app_secret:
        logger.warning("Feishu integration is not enabled, skipping callback client")
        return

    lark = _get_lark_module()

    logger.info(
        f"Initializing Feishu WebSocket client with app_id: {settings.feishu_app_id[:8]}..."
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

    logger.info("Event handler registered, creating WebSocket client...")

    _ws_client = lark.ws.Client(
        settings.feishu_app_id,
        settings.feishu_app_secret,
        event_handler=event_handler,
        log_level=lark.LogLevel.WARNING,
    )

    logger.info("WebSocket client created, starting connection...")
    try:
        _ws_client.start()
        logger.info("WebSocket client started")
    except RuntimeError:
        logger.warning(
            "WebSocket client cannot start (event loop conflict). "
            "This is expected in uvicorn reload mode. "
            "Use 'uvicorn app.main:app' without --reload for production."
        )


def start_feishu_callback_client() -> None:
    """Start the Feishu callback client in a background thread."""
    global _callback_thread

    if _callback_thread is not None and _callback_thread.is_alive():
        logger.info("Feishu callback client is already running")
        return

    _callback_thread = threading.Thread(target=_start_callback_client, daemon=True)
    _callback_thread.start()
    logger.info("Feishu callback client started in background thread")


def stop_feishu_callback_client() -> None:
    """Stop the Feishu callback client."""
    global _ws_client
    if _ws_client:
        _ws_client.stop()
        logger.info("Feishu WebSocket client stopped")


def _do_bot_p2p_chat_entered(data: Any) -> None:
    """Handle bot entered p2p chat event."""
    lark = _get_lark_module()
    logger.info(f"Bot p2p chat entered: {lark.JSON.marshal(data)}")
    return None


def _do_im_message_reaction_created_v1(data: Any) -> None:
    """Handle im.message.reaction.created_v1 event."""
    lark = _get_lark_module()
    logger.info(f"Message reaction created: {lark.JSON.marshal(data)}")
    return None


def _do_im_message_message_read_v1(data: Any) -> None:
    """Handle im.message.message_read_v1 event."""
    lark = _get_lark_module()
    logger.info(f"Message read event: {lark.JSON.marshal(data)}")
    return None


def _do_im_message_receive_v1(data: Any) -> Any:
    """Handle im.message.receive_v1 event - receive user messages."""
    try:
        lark = _get_lark_module()
        message_content = lark.JSON.marshal(data)
        logger.info(f"Message received: {message_content[:500]}...")

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
        if content:
            try:
                msg_dict = json.loads(content) if isinstance(content, str) else content
                msg_type = msg_dict.get("msg_type", "") if isinstance(msg_dict, dict) else ""
                text_content = msg_dict.get("text", "") if isinstance(msg_dict, dict) else ""

                logger.info(
                    f"Message from {sender_id}: type={msg_type}, text={text_content[:100] if text_content else 'N/A'}"
                )

                if msg_type == "text" and text_content:
                    _handle_text_message(sender_id, text_content)
            except Exception as e:
                logger.error(f"Error parsing message content: {e}")

        if message_id:
            _send_salute_reaction(message_id)
        return None

    except Exception as e:
        logger.error(f"Error processing message: {e}")
        return None


def _send_salute_reaction(message_id: str | None) -> None:
    """Add salute emoji reaction to the message."""
    if not message_id:
        return
    try:
        from app.integrations.feishu.service import get_feishu_service

        feishu = get_feishu_service()
        feishu.add_message_reaction(message_id, emoji_type="Typing")
        logger.info(f"Added salute reaction to message {message_id}")
    except Exception as e:
        logger.error(f"Error adding salute reaction: {e}")


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
        logger.info(f"Received text from {sender_id}: {text}")


def _send_help_menu(user_id: str) -> None:
    """Send help menu to user."""
    try:
        from app.integrations.feishu.service import get_feishu_service

        feishu = get_feishu_service()
        card_content = {
            "header": {
                "title": {"tag": "plain_text", "content": "IT反馈机器人帮助"},
                "template": "blue",
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": "**欢迎使用IT反馈机器人**\n\n请选择操作：",
                    },
                },
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "提交反馈"},
                            "type": "primary",
                            "value": {"action": "submit_feedback"},
                        },
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "查看状态"},
                            "type": "default",
                            "value": {"action": "check_status"},
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
        }
        feishu.send_p2p_card_message(user_id, card_content)
    except Exception as e:
        logger.error(f"Error sending help menu: {e}")


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
        logger.error(f"Error sending status info: {e}")
