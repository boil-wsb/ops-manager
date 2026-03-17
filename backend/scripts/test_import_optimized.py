"""
测试优化后的导入性能
"""
import asyncio
import httpx
import time


async def test_import_performance():
    base_url = "http://localhost:8000/api/v1"

    async with httpx.AsyncClient(timeout=120.0) as client:
        print("测试优化后的导入性能...")

        # 登录
        print("\n1. 登录...")
        login_resp = await client.post(
            f"{base_url}/auth/login",
            json={"username": "admin", "password": "admin123"}
        )
        if login_resp.status_code != 200:
            print(f"登录失败: {login_resp.status_code}")
            return

        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("登录成功")

        # 先获取发现列表
        print("\n2. 获取发现列表...")
        discovery_resp = await client.get(f"{base_url}/assets/discovery", headers=headers)
        if discovery_resp.status_code != 200:
            print(f"获取失败: {discovery_resp.status_code}")
            return

        data = discovery_resp.json()
        nodes = data.get("nodes", [])
        print(f"发现 {len(nodes)} 个待导入节点")

        if len(nodes) < 2:
            print("节点数量不足，无法测试批量导入")
            return

        # 测试导入第一个节点（会刷新缓存）
        first_node = nodes[0]
        instance1 = first_node["instance"]
        print(f"\n3. 导入第一个节点（刷新缓存）: {instance1}")
        start_time = time.time()
        import_resp1 = await client.post(
            f"{base_url}/assets/discovery/{instance1}/import",
            headers=headers
        )
        elapsed1 = time.time() - start_time
        print(f"状态码: {import_resp1.status_code}")
        print(f"耗时: {elapsed1:.2f} 秒")

        # 测试导入第二个节点（使用缓存）
        second_node = nodes[1]
        instance2 = second_node["instance"]
        print(f"\n4. 导入第二个节点（使用缓存）: {instance2}")
        start_time = time.time()
        import_resp2 = await client.post(
            f"{base_url}/assets/discovery/{instance2}/import",
            headers=headers
        )
        elapsed2 = time.time() - start_time
        print(f"状态码: {import_resp2.status_code}")
        print(f"耗时: {elapsed2:.2f} 秒")

        print(f"\n性能对比:")
        print(f"  - 首次导入（刷新缓存）: {elapsed1:.2f} 秒")
        print(f"  - 二次导入（使用缓存）: {elapsed2:.2f} 秒")
        if elapsed1 > 0:
            print(f"  - 性能提升: {(elapsed1 - elapsed2) / elapsed1 * 100:.1f}%")


if __name__ == '__main__':
    asyncio.run(test_import_performance())
