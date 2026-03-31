"""
测试 IT 反馈飞书通知功能 - 直接指定IP测试

此脚本直接发送飞书卡片通知，模拟用户提交反馈时的场景。

使用方法：
cd backend && $env:PYTHONPATH="."; python scripts/test_feedback_notification_direct.py
"""
import asyncio
import logging
import os

os.environ.setdefault("DISABLE_RATE_LIMIT", "true")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def send_test_notification_sync(
    user_id: str,
    feedback_id: int,
    client_ip: str,
    asset_name: str | None,
    description: str | None,
    contact: str | None,
) -> None:
    """同步发送飞书通知"""
    from app.integrations.feishu import get_feishu_service

    feishu_service = get_feishu_service()

    tags = [
        {"label": "反馈ID", "value": str(feedback_id)},
        {"label": "终端IP", "value": client_ip},
        {"label": "终端名称", "value": asset_name or "未知"},
        {"label": "反馈内容", "value": description or "无"},
    ]
    if contact:
        tags.append({"label": "联系方式", "value": contact})

    try:
        result = feishu_service.send_interactive_message(
            user_id=user_id,
            title="【IT反馈处理通知】",
            content="**新IT反馈待处理**",
            tags=tags,
        )
        logger.info(f"飞书通知发送成功: {result}")
    except Exception as e:
        logger.error(f"飞书通知发送失败: {e}")


async def main():
    logger.info("=== IT 反馈飞书通知直接测试 ===")

    # 直接使用指定的测试数据
    test_ip = "192.168.113.120"
    asset_name = "DESKTOP-ECECKM9"
    feedback_id = 16
    description = "卡死咯"
    contact = "17314973267"

    logger.info(f"终端IP: {test_ip}")
    logger.info(f"终端名称: {asset_name}")
    logger.info(f"反馈ID: {feedback_id}")
    logger.info(f"反馈内容: {description}")
    logger.info(f"联系方式: {contact}")

    logger.info("\n=== 直接发送飞书通知 ===")
    send_test_notification_sync(
        user_id="ou_e7e3a761a4bc2e3ae17402c67d7685ae",
        feedback_id=feedback_id,
        client_ip=test_ip,
        asset_name=asset_name,
        description=description,
        contact=contact,
    )

    logger.info("\n=== 测试完成 ===")


if __name__ == "__main__":
    asyncio.run(main())
