"""
测试资产 API - 验证资产更新功能
"""
import asyncio
import httpx
from datetime import datetime


BASE_URL = "http://localhost:8000"
HEADERS = {"Content-Type": "application/json"}


async def test_asset_update():
    """测试资产更新功能"""
    print("=" * 60)
    print("测试资产更新功能")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        # 1. 获取资产列表
        print("\n1. 获取资产列表...")
        response = await client.get(
            f"{BASE_URL}/api/v1/assets",
            params={"page": 1, "page_size": 10}
        )
        
        if response.status_code != 200:
            print(f"获取资产列表失败: {response.status_code}")
            return False
        
        data = response.json()
        assets = data.get('items', [])
        
        if not assets:
            print("没有可测试的资产")
            return False
        
        asset = assets[0]
        asset_id = asset['id']
        print(f"选择资产 ID: {asset_id}, 名称: {asset['name']}")
        
        # 2. 测试更新资产 - 只更新 owner 字段
        print("\n2. 测试更新资产 owner 字段...")
        update_data = {
            "owner": "测试负责人",
            "description": f"测试更新 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        }
        
        response = await client.put(
            f"{BASE_URL}/api/v1/assets/{asset_id}",
            json=update_data,
            headers=HEADERS
        )
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            updated = response.json()
            print(f"更新成功!")
            print(f"  owner: {updated.get('owner', 'N/A')}")
            print(f"  description: {updated.get('description', 'N/A')}")
            return True
        else:
            print(f"更新失败: {response.text}")
            return False


async def test_asset_create():
    """测试资产创建功能"""
    print("\n" + "=" * 60)
    print("测试资产创建功能")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        asset_data = {
            "asset_id": f"TEST-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "name": "测试资产",
            "asset_type": "SERVER",
            "status": "ACTIVE",
            "ip_address": "192.168.1.100",
            "owner": "测试负责人",
            "description": "这是一个测试资产"
        }

        response = await client.post(
            f"{BASE_URL}/api/v1/assets",
            json=asset_data,
            headers=HEADERS
        )

        print(f"\nPOST /api/v1/assets")
        print(f"状态码: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"创建成功!")
            print(f"  id: {data.get('id')}")
            print(f"  assetId: {data.get('assetId')}")
            print(f"  owner: {data.get('owner', 'N/A')}")
            return True
        else:
            print(f"创建失败: {response.text}")
            return False


async def main():
    print("\n资产 API 测试")
    print(f"API地址: {BASE_URL}")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    test1 = await test_asset_create()
    test2 = await test_asset_update()

    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    print(f"1. 资产创建: {'✅ 通过' if test1 else '❌ 失败'}")
    print(f"2. 资产更新: {'✅ 通过' if test2 else '❌ 失败'}")
    print("=" * 60)


if __name__ == '__main__':
    asyncio.run(main())
