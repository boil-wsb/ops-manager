"""
测试导入功能
"""
import asyncio
import httpx


async def test_import():
    base_url = "http://localhost:8000/api/v1"

    # 增加超时时间到 120 秒
    timeout = httpx.Timeout(120.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        print("测试导入 API...")

        # 登录
        print("\n1. 登录...")
        login_resp = await client.post(
            f"{base_url}/auth/login",
            json={"username": "admin", "password": "admin123"}
        )
        if login_resp.status_code != 200:
            print(f"登录失败: {login_resp.status_code}")
            print(f"响应: {login_resp.text}")
            return

        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("登录成功")

        # 先获取发现列表
        print("\n2. 获取发现列表...")
        discovery_resp = await client.get(f"{base_url}/assets/discovery", headers=headers)
        if discovery_resp.status_code != 200:
            print(f"获取失败: {discovery_resp.status_code}")
            print(f"响应: {discovery_resp.text}")
            return

        data = discovery_resp.json()
        nodes = data.get("nodes", [])
        print(f"发现 {len(nodes)} 个待导入节点")

        if not nodes:
            print("没有待导入的节点")
            return

        # 导入第一个节点
        first_node = nodes[0]
        instance = first_node["instance"]
        print(f"\n3. 导入节点: {instance}")

        import_resp = await client.post(
            f"{base_url}/assets/discovery/{instance}/import",
            headers=headers
        )
        print(f"状态码: {import_resp.status_code}")
        print(f"响应: {import_resp.text}")


if __name__ == '__main__':
    asyncio.run(test_import())
