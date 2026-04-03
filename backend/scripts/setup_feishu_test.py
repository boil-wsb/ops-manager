"""
Setup Feishu receiver and template for testing.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.db.session import get_engine


async def setup_feishu_config():
    """Create Feishu receiver and template for testing."""
    engine = get_engine()
    async with engine.begin() as conn:
        result = await conn.execute(
            text("SELECT id FROM alert_receivers WHERE name = :name"),
            {"name": "Test Feishu Receiver"}
        )
        if result.fetchone():
            print("Feishu receiver already exists")
        else:
            await conn.execute(
                text("""
                    INSERT INTO alert_receivers (name, webhook_url, auth_type, is_active, created_at, updated_at)
                    VALUES (:name, :webhook_url, 'none', true, NOW(), NOW())
                """),
                {
                    "name": "Test Feishu Receiver",
                    "webhook_url": "https://open.feishu.cn/open-apis/bot/v2/hook/REPLACE_WITH_YOUR_WEBHOOK_URL"
                }
            )
            print("Created Feishu receiver")

        result = await conn.execute(
            text("SELECT id FROM alert_templates WHERE name = :name"),
            {"name": "Test Feishu Template"}
        )
        if result.fetchone():
            print("Feishu template already exists")
        else:
            await conn.execute(
                text("""
                    INSERT INTO alert_templates (name, template_type, subject_template, body_template, is_default, is_active, created_at, updated_at)
                    VALUES (:name, 'feishu', :subject, :body, true, true, NOW(), NOW())
                """),
                {
                    "name": "Test Feishu Template",
                    "subject": "【{{.Severity}}】{{.Alertname}} - {{.Status}}",
                    "body": """**告警名称**: {{.Alertname}}
**告警状态**: {{.Status}}
**严重程度**: {{.Severity}}
**实例**: {{.Instance}}
**描述**: {{.Description}}

---
*来自 OpsManager 告警中心*"""
                }
            )
            print("Created Feishu template")

    print("\nFeishu configuration setup complete!")
    print("\nNOTE: Please replace the webhook URL with your actual Feishu webhook URL in the database.")


if __name__ == "__main__":
    asyncio.run(setup_feishu_config())
