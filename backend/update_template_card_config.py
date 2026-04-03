"""Script to update template 2 card_config."""
import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.session import get_session_maker
from app.models.alert import AlertTemplate
from sqlalchemy import select


CARD_CONFIG = {
    "schema": "2.0",
    "header": {
        "title": {
            "tag": "plain_text",
            "content": "【{{.Severity}}】{{.Alertname}}"
        },
        "template": "red",
        "text_tag_list": [
            {
                "tag": "text_tag",
                "element_id": "status_tag",
                "text": {
                    "tag": "plain_text",
                    "content": "{{.Status}}"
                },
                "color": "blue" if "{{.Status}}" == "firing" else "yellow"
            }
        ]
    },
    "body": {
        "elements": [
            {"tag": "div", "text": {"tag": "lark_md", "content": "🕐 **开始时间**：{{.StartsAt}}"}},
            {"tag": "div", "text": {"tag": "lark_md", "content": "🖥️ **故障主机**：{{.Instance}}"}},
            {"tag": "div", "text": {"tag": "lark_md", "content": "📋 **事件详情**：{{.Description}}"}},
            {"tag": "hr"},
            {
                "tag": "column_set",
                "flex_mode": "center",
                "columns": [
                    {
                        "tag": "column",
                        "width": "stretch",
                        "elements": [
                            {
                                "tag": "button",
                                "text": {"tag": "plain_text", "content": "转交 IT 处理"},
                                "type": "default",
                                "width": "fill",
                                "name": "transfer_it",
                                "behaviors": [{"type": "callback", "value": {"action": "transfer_it_{{$alertId}}"}}]
                            }
                        ]
                    },
                    {
                        "tag": "column",
                        "width": "stretch",
                        "elements": [
                            {
                                "tag": "button",
                                "text": {"tag": "plain_text", "content": "知道了，我来处理"},
                                "type": "primary",
                                "width": "fill",
                                "name": "acknowledge",
                                "behaviors": [{"type": "callback", "value": {"action": "acknowledge_{{$alertId}}"}}]
                            }
                        ]
                    }
                ]
            }
        ]
    }
}


async def update_template():
    session_maker = get_session_maker()
    async with session_maker() as db:
        result = await db.execute(
            select(AlertTemplate).where(AlertTemplate.id == 2)
        )
        template = result.scalar_one_or_none()

        if template:
            template.card_config = json.loads(json.dumps(CARD_CONFIG, ensure_ascii=False))
            await db.commit()
            print(f"Updated template 2 card_config")
        else:
            print("Template 2 not found")


if __name__ == "__main__":
    asyncio.run(update_template())
