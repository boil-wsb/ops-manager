"""
Feishu callback handler for long connection (WebSocket) mode.
"""
import logging
import threading
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

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
        action_tag = getattr(action, 'tag', None)
        value = action.value if hasattr(action, 'value') and action.value else {}
        form_value = getattr(action, 'form_value', None)
        input_value = getattr(action, 'input_value', None)
        name = getattr(action, 'name', None)

        if action_tag == "input":
            logger.info("Ignoring input tag callback, waiting for form submission")
            from lark_oapi.event.callback.model.p2_card_action_trigger import P2CardActionTriggerResponse
            return P2CardActionTriggerResponse(None)

        button_action = value.get("action", "") if isinstance(value, dict) else ""
        if not button_action and name:
            button_action = name

        open_message_id = None
        if hasattr(data.event, 'context') and data.event.context:
            open_message_id = data.event.context.open_message_id if hasattr(data.event.context, 'open_message_id') else None

        if button_action.startswith("handle_"):
            feedback_id = button_action.replace("handle_", "")
            threading.Thread(target=_handle_feedback_sync, args=(feedback_id,), daemon=True).start()

            if open_message_id:
                threading.Thread(target=_update_card_to_handling, args=(open_message_id, feedback_id), daemon=True).start()

            resp = {"toast": {"type": "info", "content": f"已开始处理，请填写处理方式"}}

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
                from lark_oapi.event.callback.model.p2_card_action_trigger import P2CardActionTriggerResponse
                return P2CardActionTriggerResponse(resp)

            logger.info(f"Finish feedback {feedback_id}, notes: '{notes}'")

            if not notes or not notes.strip():
                resp = {"toast": {"type": "error", "content": "请填写处理方式"}}
                from lark_oapi.event.callback.model.p2_card_action_trigger import P2CardActionTriggerResponse
                return P2CardActionTriggerResponse(resp)

            threading.Thread(target=_finish_feedback_sync, args=(feedback_id, notes), daemon=True).start()

            if open_message_id:
                threading.Thread(target=_update_card_to_resolved, args=(open_message_id, feedback_id, notes), daemon=True).start()
            resp = {"toast": {"type": "info", "content": f"处理完成，已通知提交者"}}

        else:
            resp = {"toast": {"type": "info", "content": f"收到回调: {button_action}"}}

        from lark_oapi.event.callback.model.p2_card_action_trigger import P2CardActionTriggerResponse
        return P2CardActionTriggerResponse(resp)

    except Exception as e:
        logger.error(f"Error processing card action: {e}")
        resp = {"toast": {"type": "error", "content": f"处理失败: {str(e)}"}}
        from lark_oapi.event.callback.model.p2_card_action_trigger import P2CardActionTriggerResponse
        return P2CardActionTriggerResponse(resp)


def _handle_feedback_sync(feedback_id: str) -> None:
    """Mark feedback as handling using sync database operations."""
    from sqlalchemy import create_engine, text
    from app.config import settings

    try:
        sync_db_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
        engine = create_engine(sync_db_url, pool_pre_ping=True)

        with engine.connect() as conn:
            conn.execute(text("UPDATE it_feedbacks SET status = 'handling' WHERE id = :id"), {"id": int(feedback_id)})
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
                {"open_message_id": open_message_id}
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
                {"id": int(feedback_id)}
            )
            row = result.fetchone()
            client_ip = row[0] if row else None
            description = row[1] if row else ""
            customer = row[2] if row else None
            feishu_open_id = row[3] if row else None
            resolver_name = row[4] if row else "IT管理员"

            conn.execute(
                text("UPDATE it_feedbacks SET status = 'resolved', notes = :notes WHERE id = :id"),
                {"id": int(feedback_id), "notes": notes}
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
                logger.info(f"Notification sent to feishu_open_id {feishu_open_id} (customer: {customer}) for feedback {feedback_id}")
            except Exception as e:
                logger.error(f"Failed to send notification: {e}")
        else:
            logger.warning(f"No feishu_open_id found for customer {customer}, skipping notification")

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
            conn.execute(text("UPDATE it_feedbacks SET status = 'resolved' WHERE id = :id"), {"id": int(feedback_id)})
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
                {"id": int(feedback_id)}
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
                {"id": int(feedback_id)}
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


def _start_callback_client() -> None:
    """Start the Feishu WebSocket callback client."""
    global _ws_client

    if not settings.feishu_enable or not settings.feishu_app_id or not settings.feishu_app_secret:
        logger.warning("Feishu integration is not enabled, skipping callback client")
        return

    lark = _get_lark_module()

    logger.info(f"Initializing Feishu WebSocket client with app_id: {settings.feishu_app_id[:8]}...")

    event_handler = (
        lark.EventDispatcherHandler.builder("", "")
        .register_p2_card_action_trigger(_do_card_action_trigger)
        .register_p2_im_chat_access_event_bot_p2p_chat_entered_v1(_do_bot_p2p_chat_entered)
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
    except Exception as e:
        logger.error(f"WebSocket client start failed: {e}")
        raise


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
