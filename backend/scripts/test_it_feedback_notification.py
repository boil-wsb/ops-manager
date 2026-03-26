"""
测试 IT 反馈飞书通知功能

此脚本模拟用户提交卡顿反馈，测试当 client_ip 匹配终端资产时是否正确发送飞书卡片通知。

前置条件：
1. 飞书应用已配置（FEISHU_APP_ID, FEISHU_APP_SECRET, FEISHU_ENABLE=true）
2. 数据库中存在一个 ip_address 为测试IP的 TERMINAL 类型资产

使用方法：
cd backend && $env:PYTHONPATH="."; python scripts/test_it_feedback_notification.py
"""
import asyncio
import logging
import os

os.environ.setdefault("DISABLE_RATE_LIMIT", "true")

from sqlalchemy import select

from app.db.session import get_session_maker
from app.models.asset import Asset, AssetType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def check_existing_assets(db):
    """检查数据库中现有的终端资产"""
    result = await db.execute(
        select(Asset).where(Asset.asset_type == AssetType.TERMINAL).limit(10)
    )
    assets = result.scalars().all()

    if assets:
        logger.info("=== 现有终端资产 ===")
        for asset in assets:
            logger.info(f"ID: {asset.id}, Name: {asset.name}, IP: {asset.ip_address}, Owner: {asset.owner_name}")
        return assets
    else:
        logger.warning("没有找到终端资产，请先创建测试数据")
        return []


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


async def create_test_feedback(db):
    """创建测试反馈数据"""
    test_ip = "192.168.113.120"

    result = await db.execute(
        select(Asset).where(
            Asset.ip_address == test_ip,
            Asset.asset_type == AssetType.TERMINAL
        )
    )
    asset = result.scalar_one_or_none()

    if not asset:
        logger.info(f"没有找到 IP 为 {test_ip} 的终端资产，尝试查找任意终端资产")
        result = await db.execute(
            select(Asset).where(Asset.asset_type == AssetType.TERMINAL).limit(1)
        )
        asset = result.scalar_one_or_none()
        if asset:
            test_ip = asset.ip_address
            logger.info(f"使用现有终端资产: {asset.name}, IP: {test_ip}")

    if not asset:
        logger.error("无法测试：没有可用的终端资产")
        return None, None

    logger.info("=== 准备发送测试反馈 ===")
    logger.info(f"终端IP: {test_ip}")
    logger.info(f"终端名称: {asset.name}")

    from app.models.it_feedback import ITFeedback

    test_feedback = ITFeedback(
        computer_type="desktop",
        usage_years="3-5",
        lag_level="3",
        lag_scenarios="开机,办公软件",
        description="测试反馈：电脑开机很慢，运行缓慢",
        contact="test@example.com",
        client_ip=test_ip,
        status="pending",
    )

    db.add(test_feedback)
    await db.commit()
    await db.refresh(test_feedback)

    logger.info(f"测试反馈已创建，ID: {test_feedback.id}")

    return test_feedback, asset


async def cleanup_test_feedback(db, feedback_id):
    """清理测试反馈"""
    from app.models.it_feedback import ITFeedback
    result = await db.execute(
        select(ITFeedback).where(ITFeedback.id == feedback_id)
    )
    feedback_to_delete = result.scalar_one_or_none()
    if feedback_to_delete:
        await db.delete(feedback_to_delete)
        await db.commit()
        logger.info("测试反馈已清理")


async def main():
    logger.info("=== IT 反馈飞书通知测试 ===")

    session_maker = get_session_maker()
    async with session_maker() as db:
        try:
            assets = await check_existing_assets(db)
            if not assets:
                logger.warning("继续测试，但不验证资产匹配逻辑")

            logger.info("\n=== 创建测试反馈 ===")
            test_feedback, asset = await create_test_feedback(db)

            if not test_feedback:
                logger.error("测试反馈创建失败")
                return

            test_ip = test_feedback.client_ip
            asset_name = asset.name if asset else "未知"

            logger.info("\n=== 直接发送飞书通知 ===")
            send_test_notification_sync(
                user_id="ou_e7e3a761a4bc2e3ae17402c67d7685ae",
                feedback_id=test_feedback.id,
                client_ip=test_ip,
                asset_name=asset_name,
                description=test_feedback.description,
                contact=test_feedback.contact,
            )

            logger.info("\n=== 清理测试数据 ===")
            await cleanup_test_feedback(db, test_feedback.id)

            logger.info("\n=== 测试完成 ===")
        except Exception as e:
            logger.error(f"测试过程出错: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(main())
