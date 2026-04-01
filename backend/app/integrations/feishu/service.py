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
        msg_type: str,
        content: str | dict[str, Any],
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
                f"[Feishu] Failed to send message - user_id={user_id}, code={response.code}, msg={response.msg}"
            )
            raise RuntimeError(f"Failed to send message: {response.msg}")

        logger.info(
            f"[Feishu] Message sent successfully - user_id={user_id}, message_id={response.data.message_id if response.data else None}"
        )

        if response.data:
            msg_id = getattr(response.data, 'message_id', None)
            return {
                "message_id": msg_id,
                "code": response.code,
                "msg": response.msg,
            }
        return {
            "message_id": None,
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
        buttons: list[dict[str, str]] | None = None,
        jump_url: str | None = None,
        header_template: str = "orange",
    ) -> dict[str, Any]:
        tag_icon_map = {
            "负责人": "👤",
            "终端IP": "📍",
            "终端名称": "🖥️",
            "反馈内容": "💬",
            "联系方式": "📞",
            "卡顿程度": "⚡",
            "终端类型": "💻",
            "使用年限": "⏰",
            "提交时间": "⏱️",
        }

        elements = []

        elements.append({"tag": "hr"})

        if tags:
            for tag in tags:
                label = tag.get('label', '')
                value = tag.get('value', '')
                icon = tag_icon_map.get(label, "")

                elements.append({
                    "tag": "column_set",
                    "flex_mode": "flow",
                    "columns": [
                        {
                            "tag": "column",
                            "width": "auto",
                            "elements": [
                                {
                                    "tag": "div",
                                    "text": {
                                        "tag": "lark_md",
                                        "content": f"**{icon} {label}**"
                                    }
                                }
                            ]
                        },
                        {
                            "tag": "column",
                            "width": "auto",
                            "elements": [
                                {
                                    "tag": "div",
                                    "text": {
                                        "tag": "lark_md",
                                        "content": value
                                    }
                                }
                            ]
                        }
                    ]
                })

        if buttons:
            elements.append({"tag": "hr"})

            btn_column_elements = []
            for btn in buttons:
                btn_text = btn.get("text", "按钮")
                btn_value = str(btn.get("value", btn_text))
                btn_type = btn.get("type", "primary")

                btn_column_elements.append({
                    "tag": "button",
                    "text": {
                        "tag": "plain_text",
                        "content": btn_text
                    },
                    "type": btn_type,
                    "width": "fill",
                    "behaviors": [
                        {
                            "type": "callback",
                            "value": {
                                "action": btn_value
                            }
                        }
                    ]
                })

            elements.append({
                "tag": "column_set",
                "flex_mode": "right_to_left",
                "columns": [
                    {
                        "tag": "column",
                        "width": "stretch",
                        "elements": btn_column_elements
                    }
                ]
            })

        card_content = {
            "schema": "2.0",
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": title
                },
                "template": header_template
            },
            "body": {
                "elements": elements
            }
        }

        return self.send_message_to_user(
            user_id=user_id,
            msg_type="interactive",
            content=card_content,
        )

    def update_card_to_handling(
        self,
        open_message_id: str,
        feedback_id: str,
        responsible_name: str = ""
    ) -> dict[str, Any]:
        """Update card to handling status with input field for resolution notes."""
        card_content = {
            "schema": "2.0",
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": "【终端卡顿 IT 反馈】"
                },
                "template": "blue"
            },
            "body": {
                "elements": [
                    {"tag": "hr"},
                    {
                        "tag": "column_set",
                        "flex_mode": "flow",
                        "columns": [
                            {"tag": "column", "width": "auto", "elements": [{"tag": "div", "text": {"tag": "lark_md", "content": "**👤 负责人**"}}]},
                            {"tag": "column", "width": "auto", "elements": [{"tag": "div", "text": {"tag": "lark_md", "content": responsible_name or "待分配"}}]}
                        ]
                    },
                    {
                        "tag": "column_set",
                        "flex_mode": "flow",
                        "columns": [
                            {"tag": "column", "width": "auto", "elements": [{"tag": "div", "text": {"tag": "lark_md", "content": "**⚡ 处理状态**"}}]},
                            {"tag": "column", "width": "auto", "elements": [{"tag": "div", "text": {"tag": "lark_md", "content": "处理中"}}]}
                        ]
                    },
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": "**📝 处理方式**"
                        }
                    },
                    {
                        "tag": "form",
                        "name": "resolution_form",
                        "elements": [
                            {
                                "tag": "input",
                                "element_id": f"notes_input_{feedback_id}",
                                "name": "notes",
                                "placeholder": {
                                    "tag": "plain_text",
                                    "content": "填写处理方式（必填）"
                                }
                            },
                            {
                                "tag": "button",
                                "text": {
                                    "tag": "plain_text",
                                    "content": "🔧 提交处理"
                                },
                                "type": "primary",
                                "width": "fill",
                                "name": "submit_resolution",
                                "form_action_type": "submit"
                            }
                        ]
                    },
                    {"tag": "hr"}
                ]
            }
        }

        return self._patch_message(open_message_id, card_content)

    def update_card_to_resolved(
        self,
        open_message_id: str,
        feedback_id: str,
        notes: str,
        responsible_name: str = "",
        client_ip: str = "",
        terminal_name: str = "",
        description: str = "",
        contact: str = "",
    ) -> dict[str, Any]:
        """Update card to resolved status."""
        elements = []

        elements.append({"tag": "hr"})

        elements.append({
            "tag": "column_set",
            "flex_mode": "flow",
            "columns": [
                {"tag": "column", "width": "auto", "elements": [{"tag": "div", "text": {"tag": "lark_md", "content": "**👤 反馈提交人**"}}]},
                {"tag": "column", "width": "auto", "elements": [{"tag": "div", "text": {"tag": "lark_md", "content": responsible_name or "待分配"}}]}
            ]
        })

        elements.append({
            "tag": "column_set",
            "flex_mode": "flow",
            "columns": [
                {"tag": "column", "width": "auto", "elements": [{"tag": "div", "text": {"tag": "lark_md", "content": "**⚡ 处理状态**"}}]},
                {"tag": "column", "width": "auto", "elements": [{"tag": "div", "text": {"tag": "lark_md", "content": "✅ 已解决"}}]}
            ]
        })

        if client_ip:
            elements.append({
                "tag": "column_set",
                "flex_mode": "flow",
                "columns": [
                    {"tag": "column", "width": "auto", "elements": [{"tag": "div", "text": {"tag": "lark_md", "content": "**📍 终端IP**"}}]},
                    {"tag": "column", "width": "auto", "elements": [{"tag": "div", "text": {"tag": "lark_md", "content": client_ip}}]}
                ]
            })

        if terminal_name:
            elements.append({
                "tag": "column_set",
                "flex_mode": "flow",
                "columns": [
                    {"tag": "column", "width": "auto", "elements": [{"tag": "div", "text": {"tag": "lark_md", "content": "**🖥️ 终端名称**"}}]},
                    {"tag": "column", "width": "auto", "elements": [{"tag": "div", "text": {"tag": "lark_md", "content": terminal_name}}]}
                ]
            })

        if description:
            elements.append({
                "tag": "column_set",
                "flex_mode": "flow",
                "columns": [
                    {"tag": "column", "width": "auto", "elements": [{"tag": "div", "text": {"tag": "lark_md", "content": "**💬 反馈内容**"}}]},
                    {"tag": "column", "width": "auto", "elements": [{"tag": "div", "text": {"tag": "lark_md", "content": description}}]}
                ]
            })

        if contact:
            elements.append({
                "tag": "column_set",
                "flex_mode": "flow",
                "columns": [
                    {"tag": "column", "width": "auto", "elements": [{"tag": "div", "text": {"tag": "lark_md", "content": "**📞 联系方式**"}}]},
                    {"tag": "column", "width": "auto", "elements": [{"tag": "div", "text": {"tag": "lark_md", "content": contact}}]}
                ]
            })

        if notes:
            elements.append({
                "tag": "column_set",
                "flex_mode": "flow",
                "columns": [
                    {"tag": "column", "width": "auto", "elements": [{"tag": "div", "text": {"tag": "lark_md", "content": "**📝 处理方式**"}}]},
                    {"tag": "column", "width": "auto", "elements": [{"tag": "div", "text": {"tag": "lark_md", "content": notes}}]}
                ]
            })

        elements.append({"tag": "hr"})

        card_content = {
            "schema": "2.0",
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": "【终端卡顿 IT 反馈】"
                },
                "template": "green"
            },
            "body": {
                "elements": elements
            }
        }

        return self._patch_message(open_message_id, card_content)

    def _patch_message(self, open_message_id: str, card_content: dict) -> dict[str, Any]:
        """Patch a message with updated card content."""
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

            response = (
                lark.Client.builder()
                .app_id(settings.feishu_app_id)
                .app_secret(settings.feishu_app_secret)
                .build()
            ).im.v1.message.patch(request)

            if response.success():
                logger.info(f"[Feishu] Card updated successfully - message_id={open_message_id}")
                return {"success": True}
            else:
                logger.error(f"[Feishu] Failed to update card - message_id={open_message_id}, code={response.code}, msg={response.msg}")
                return {"success": False, "error": f"{response.code} - {response.msg}"}
        except Exception as e:
            logger.error(f"[Feishu] Error patching message - message_id={open_message_id}, error={e}")
            return {"success": False, "error": str(e)}

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
            title="【终端卡顿 IT 反馈】",
            content="",
            tags=tags,
            header_template="green",
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
