"""
Feishu (Lark) notification service using lark_oapi SDK.
"""

from typing import Any

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class FeishuNotificationService:
    """Service for sending notifications to Feishu (Lark) via lark_oapi SDK."""

    def __init__(self):
        """Initialize Feishu notification service lazily."""
        self._enabled = settings.feishu_enable and bool(
            settings.feishu_app_id and settings.feishu_app_secret
        )
        self._client = None

    def _get_client(self):
        """Lazily initialize and return the lark_oapi client."""
        if self._client is None and self._enabled:
            import lark_oapi as lark

            self._client = (
                lark.Client.builder()
                .app_id(settings.feishu_app_id)
                .app_secret(settings.feishu_app_secret)
                .log_level(lark.LogLevel.INFO)
                .build()
            )
        return self._client

    def is_configured(self) -> bool:
        """Check if Feishu service is properly configured."""
        return self._enabled

    def _check_enabled(self) -> None:
        """Check if service is enabled, raise if not."""
        if not self._enabled:
            raise RuntimeError("Feishu service is not enabled or not properly configured")

    def send_p2p_card_message(
        self,
        open_id: str,
        card_content: dict,
    ) -> dict[str, Any]:
        """Send interactive card message to user via P2P using lark_oapi SDK.

        Returns:
            dict with 'success' (bool) and 'message_id' (str | None)
        """
        self._check_enabled()

        import lark_oapi as lark
        from lark_oapi.api.im.v1 import CreateMessageRequest, CreateMessageRequestBody

        try:
            request = (
                CreateMessageRequest.builder()
                .receive_id_type("open_id")
                .request_body(
                    CreateMessageRequestBody.builder()
                    .receive_id(open_id)
                    .msg_type("interactive")
                    .content(lark.JSON.marshal(card_content))
                    .build()
                )
                .build()
            )

            response = self._get_client().im.v1.message.create(request)

            if response.success():
                message_id = response.data.message_id if response.data else None
                logger.info(
                    f"P2P card message sent to open_id: {open_id}, message_id: {message_id}"
                )
                return {"success": True, "message_id": message_id}
            else:
                logger.error(f"Failed to send P2P card: code={response.code}, msg={response.msg}")
                return {"success": False, "message_id": None}

        except Exception as exc:
            logger.error(f"Error sending P2P card message: {str(exc)}")
            return {"success": False, "message_id": None}

    def send_p2p_text_message(
        self,
        open_id: str,
        text: str,
    ) -> bool:
        """Send text message to user via P2P using lark_oapi SDK."""
        self._check_enabled()

        import lark_oapi as lark
        from lark_oapi.api.im.v1 import CreateMessageRequest, CreateMessageRequestBody

        try:
            request = (
                CreateMessageRequest.builder()
                .receive_id_type("open_id")
                .request_body(
                    CreateMessageRequestBody.builder()
                    .receive_id(open_id)
                    .msg_type("text")
                    .content(lark.JSON.marshal({"text": text}))
                    .build()
                )
                .build()
            )

            response = self._get_client().im.v1.message.create(request)

            if response.success():
                logger.info(f"P2P text message sent to open_id: {open_id}")
                return True
            else:
                logger.error(f"Failed to send P2P text: code={response.code}, msg={response.msg}")
                return False

        except Exception as exc:
            logger.error(f"Error sending P2P text message: {str(exc)}")
            return False

    def build_alert_card(
        self,
        alertname: str,
        status: str,
        severity: str,
        instance: str,
        description: str,
        starts_at: str,
    ) -> dict[str, Any]:
        """Build Feishu interactive card for alert notification."""
        header_template = (
            "red" if severity == "critical" else ("orange" if severity == "warning" else "blue")
        )

        card = {
            "schema": "2.0",
            "header": {
                "title": {"tag": "plain_text", "content": f"【{severity.upper()}】{alertname}"},
                "template": header_template,
            },
            "body": {
                "elements": [
                    {
                        "tag": "div",
                        "text": {"tag": "lark_md", "content": f"🔴 **告警状态**：{status.upper()}"},
                    },
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": f"⚠️ **严重程度**：{severity.upper()}",
                        },
                    },
                    {
                        "tag": "div",
                        "text": {"tag": "lark_md", "content": f"🖥️ **故障主机**：{instance}"},
                    },
                    {
                        "tag": "div",
                        "text": {"tag": "lark_md", "content": f"📋 **事件详情**：{description}"},
                    },
                    {
                        "tag": "div",
                        "text": {"tag": "lark_md", "content": f"🕐 **开始时间**：{starts_at}"},
                    },
                    {"tag": "hr"},
                    {
                        "tag": "div",
                        "text": {"tag": "lark_md", "content": "*来自 OpsManager 告警中心*"},
                    },
                ]
            },
        }

        return card

    def update_card_message(self, open_message_id: str, card_content: dict) -> dict[str, Any]:
        """Update an existing Feishu card message.

        Returns:
            dict with 'success' (bool) and optional 'error' message
        """
        self._check_enabled()

        import lark_oapi as lark

        try:
            request = (
                lark.im.v1.PatchMessageRequest.builder()
                .message_id(open_message_id)
                .request_body(
                    lark.im.v1.PatchMessageRequestBody.builder()
                    .content(lark.JSON.marshal(card_content))
                    .build()
                )
                .build()
            )

            response = self._get_client().im.v1.message.patch(request)

            if response.success():
                logger.info(f"Card message updated: open_message_id={open_message_id}")
                return {"success": True}
            else:
                logger.error(f"Failed to update card: code={response.code}, msg={response.msg}")
                return {"success": False, "error": f"{response.code} - {response.msg}"}

        except Exception as exc:
            logger.error(f"Error updating card message: {str(exc)}")
            return {"success": False, "error": str(exc)}

    def build_resolved_card(
        self,
        alertname: str,
        severity: str,
        instance: str,
    ) -> dict[str, Any]:
        """Build Feishu card for resolved alert without action buttons.

        Returns:
            Card content dict for resolved alert notification.
        """
        card = {
            "schema": "2.0",
            "header": {
                "title": {"tag": "plain_text", "content": f"🟢 {alertname}"},
                "template": "green",
            },
            "body": {
                "elements": [
                    {
                        "tag": "div",
                        "text": {"tag": "lark_md", "content": f"📋 **告警名称**：{alertname}"},
                    },
                    {
                        "tag": "div",
                        "text": {"tag": "lark_md", "content": f"🖥️ **故障主机**：{instance}"},
                    },
                    {"tag": "hr"},
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": "<font color='green'>✅ 该告警已恢复</font>",
                        },
                    },
                ]
            },
        }

        return card


def get_feishu_notification_service() -> FeishuNotificationService:
    """Get or create Feishu notification service singleton (lazy initialization)."""
    global feishu_notification_service
    if feishu_notification_service is None:
        feishu_notification_service = FeishuNotificationService()
    return feishu_notification_service


feishu_notification_service: FeishuNotificationService | None = None
