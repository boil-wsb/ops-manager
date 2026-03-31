"""
完整测试 IT 反馈流程 - 包括资产查询

此脚本模拟完整的反馈提交流程：
1. 创建反馈
2. 根据 client_ip 查询终端资产
3. 发送飞书通知

使用方法：
cd backend && $env:PYTHONPATH="."; python scripts/test_feedback_full_flow.py
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


def send_notification(
    user_id: str,
    feedback_id: int,
    client_ip: str,
    asset_name: str | None,
    description: str | None,
    contact: str | None,
) -> None:
    """发送飞书通知"""
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
    logger.info("=== 完整 IT 反馈流程测试 ===")

    # 测试 IP
    test_ip = "192.168.113.120"
    logger.info(f"测试 client_ip: {test_ip}")

    session_maker = get_session_maker()
    async with session_maker() as db:
        # Step 1: 查询匹配的终端资产
        logger.info("\n=== Step 1: 查询终端资产 ===")
        logger.info(f"查询条件: ip_address = '{test_ip}' AND asset_type = '{AssetType.TERMINAL}'")

        result = await db.execute(
            select(Asset).where(
                Asset.ip_address == test_ip,
                Asset.asset_type == AssetType.TERMINAL
            )
        )
        asset = result.scalar_one_or_none()

        logger.info(f"AssetType.TERMINAL = '{AssetType.TERMINAL}'")
        logger.info(f"查询结果: {asset}")

        if asset:
            logger.info(f"找到匹配的终端资产!")
            logger.info(f"  - ID: {asset.id}")
            logger.info(f"  - Name: {asset.name}")
            logger.info(f"  - IP: {asset.ip_address}")
            logger.info(f"  - asset_type: {asset.asset_type}")

            # Step 2: 发送飞书通知
            logger.info("\n=== Step 2: 发送飞书通知 ===")
            send_notification(
                user_id="ou_e7e3a761a4bc2e3ae17402c67d7685ae",
                feedback_id=999,  # 模拟反馈ID
                client_ip=test_ip,
                asset_name=asset.name,
                description="完整流程测试反馈",
                contact="13800138000",
            )
        else:
            logger.warning("没有找到匹配的终端资产!")

            # Debug: 尝试不带 asset_type 过滤的查询
            logger.info("\n=== Debug: 不带 asset_type 过滤的查询 ===")
            result = await db.execute(
                select(Asset).where(Asset.ip_address == test_ip)
            )
            all_assets = result.scalars().all()
            logger.info(f"IP={test_ip} 的所有资产: {all_assets}")
            for a in all_assets:
                logger.info(f"  - ID: {a.id}, Name: {a.name}, asset_type: {a.asset_type}")

    logger.info("\n=== 测试完成 ===")


if __name__ == "__main__":
    asyncio.run(main())
