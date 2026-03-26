"""
Feishu service for sending messages.
"""
import logging
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


class FeishuService:
    def __init__(self) -> None:
        self._client: lark.Client | None = None  # noqa: F821
        self._enabled = settings.feishu_enable and bool(
            settings.feishu_app_id and settings.feishu_app_secret
        )
        if self._enabled:
            import lark_oapi as lark
            self._client = lark.Client.builder() \
                .app_id(settings.feishu_app_id) \
                .app_secret(settings.feishu_app_secret) \
                .log_level(lark.LogLevel.INFO) \
                .build()

    def _check_enabled(self) -> None:
        if not self._enabled:
            raise RuntimeError("Feishu integration is not enabled")

    def _get_client(self) -> "lark.Client":  # noqa: F821
        if self._client is None:
            raise RuntimeError("Feishu client not initialized")
        return self._client

    def send_message_to_user(
        self,
        user_id: str,
        msg_type: str = "text",
        content: str | dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        import lark_oapi as lark
        from lark_oapi.api.im.v1 import CreateMessageRequest, CreateMessageRequestBody

        self._check_enabled()
        client = self._get_client()

        message_content = content if isinstance(content, (str, dict)) else {"text": content or ""}

        request: CreateMessageRequest = (
            CreateMessageRequest.builder()
            .receive_id_type("open_id")
            .request_body(
                CreateMessageRequestBody.builder()
                .receive_id(user_id)
                .msg_type(msg_type)
                .content(lark.JSON.marshal(message_content))
                .build()
            )
            .build()
        )

        response = client.im.v1.message.create(request)

        if not response.success():
            logger.error(
                "Failed to send Feishu message",
                extra={
                    "code": response.code,
                    "msg": response.msg,
                    "user_id": user_id,
                },
            )
            raise RuntimeError(f"Failed to send message: {response.msg}")

        logger.info(
            "Feishu message sent successfully",
            extra={"user_id": user_id, "message_id": response.data.message_id if response.data else None},
        )

        return {
            "message_id": response.data.message_id if response.data else None,
            "code": response.code,
            "msg": response.msg,
        }

    def send_text_message(self, user_id: str, text: str) -> dict[str, Any]:
        return self.send_message_to_user(
            user_id=user_id,
            msg_type="text",
            content={"text": text},
        )

    def send_interactive_message(
        self,
        user_id: str,
        title: str,
        content: str,
        tags: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        card_content = {
            "header": {
                "title": {"tag": "plain_text", "content": title},
                "template": "blue",
            },
            "elements": [
                {"tag": "div", "text": {"tag": "lark_md", "content": content}},
            ],
        }
        if tags:
            tag_content = "".join(
                f"• {tag.get('label', '')}: {tag.get('value', '')}\n"
                for tag in tags
            )
            card_content["elements"].append(
                {"tag": "div", "text": {"tag": "lark_md", "content": tag_content}}
            )

        return self.send_message_to_user(
            user_id=user_id,
            msg_type="interactive",
            content=card_content,
        )

    def send_it_feedback_resolved(
        self,
        user_id: str,
        feedback_id: int,
        feedback_content: str,
        resolved_by: str,
        notes: str | None = None,
    ) -> dict[str, Any]:
        tags = [
            {"label": "处理人", "value": resolved_by},
            {"label": "反馈内容", "value": feedback_content},
        ]
        if notes:
            tags.append({"label": "处理备注", "value": notes})

        return self.send_interactive_message(
            user_id=user_id,
            title="【IT反馈处理通知】",
            content=f"您的IT反馈（ID: {feedback_id}）已处理完成",
            tags=tags,
        )


def create_event_handler(
    message_handler: Any | None = None,
    customized_handler: Any | None = None,
) -> "EventDispatcherHandler":  # noqa: F821
    import lark_oapi as lark
    from lark_oapi.event.dispatcher_handler import EventDispatcherHandler

    encrypt_key = getattr(settings, "feishu_encrypt_key", "") or ""
    verification_token = getattr(settings, "feishu_verification_token", "") or ""

    handler = EventDispatcherHandler.builder(
        encrypt_key,
        verification_token,
        lark.LogLevel.INFO,
    )

    if message_handler:
        handler.register_p2_im_message_receive_v1(message_handler)
    if customized_handler:
        for event_key, func in customized_handler.items():
            handler.register_p1_customized_event(event_key, func)

    return handler.build()


def create_ws_client(
    event_handler: "EventDispatcherHandler",  # noqa: F821
) -> "lark.ws.Client":  # noqa: F821
    import lark_oapi as lark

    return lark.ws.Client(
        settings.feishu_app_id,
        settings.feishu_app_secret,
        event_handler=event_handler,
        log_level=lark.LogLevel.INFO,
    )


def get_feishu_service() -> FeishuService:
    """Get or create Feishu service singleton (lazy initialization)."""
    global feishu_service
    if feishu_service is None:
        feishu_service = FeishuService()
    return feishu_service


feishu_service: "FeishuService | None" = None
