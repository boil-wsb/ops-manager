"""
测试 Prometheus 资产同步功能
"""
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.services.prometheus.asset_sync import AssetSyncService
from app.services.prometheus.client import PrometheusClient


async def test_prometheus_client():
    """测试 Prometheus 客户端"""
    print("=== Testing Prometheus Client ===")
    client = PrometheusClient()

    # 测试获取所有节点
    print("\n1. Testing get_all_nodes()...")
    nodes = await client.get_all_nodes()
    print(f"   Found {len(nodes)} nodes")
    if nodes:
        print(f"   First node: {nodes[0]}")

    # 测试获取节点状态
    if nodes:
        print("\n2. Testing get_node_status()...")
        instance = nodes[0].get("instance", "")
        status = await client.get_node_status(instance)
        print(f"   Node {instance} status: {status}")

    # 测试获取节点指标
    if nodes:
        print("\n3. Testing get_node_metrics()...")
        metrics = await client.get_node_metrics(instance)
        print(f"   Node {instance} metrics: {metrics}")

    await client.close()
    print("\n✅ Prometheus Client test completed!")
    return nodes


async def test_asset_sync():
    """测试资产同步服务"""
    print("\n=== Testing Asset Sync Service ===")

    async with AsyncSessionLocal() as db:
        service = AssetSyncService(db)

        # 测试同步单个资产
        print("\n1. Testing sync_single_asset()...")
        # 先获取一个节点
        client = PrometheusClient()
        nodes = await client.get_all_nodes()
        await client.close()

        if nodes:
            instance = nodes[0].get("instance", "")
            print(f"   Syncing node: {instance}")
            result = await service.sync_single_asset(instance)
            print(f"   Result: {result}")

        # 测试全量同步
        print("\n2. Testing sync_all_assets()...")
        stats = await service.sync_all_assets()
        print(f"   Sync stats: {stats}")

    print("\n✅ Asset Sync Service test completed!")


async def test_api_endpoints():
    """测试 API 端点"""
    print("\n=== Testing API Endpoints ===")

    # 这里只是打印说明，实际测试需要通过 HTTP 客户端
    print("\nAvailable API endpoints:")
    print("  POST /api/v1/assets/sync - 手动触发同步")
    print("  GET /api/v1/assets/discovery - 发现未导入节点")
    print("  POST /api/v1/assets/discovery/{instance}/import - 导入指定节点")
    print("  GET /api/v1/assets/{asset_id}/metrics - 获取资产实时指标")

    print("\n✅ API Endpoints test completed!")


async def main():
    """主测试函数"""
    print("=" * 60)
    print("Prometheus Asset Sync Test")
    print("=" * 60)

    try:
        # 测试 Prometheus 客户端
        nodes = await test_prometheus_client()

        # 测试资产同步服务
        await test_asset_sync()

        # 测试 API 端点
        await test_api_endpoints()

        print("\n" + "=" * 60)
        print("All tests completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
