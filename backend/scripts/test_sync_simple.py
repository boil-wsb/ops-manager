"""
简单测试同步 API
"""
import asyncio
import httpx
import traceback


async def test_sync():
    base_url = "http://localhost:8000/api/v1"

    async with httpx.AsyncClient(timeout=60.0) as client:
        print("测试同步 API...")

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

        # 测试同步 API
        print("\n2. 测试 /assets/sync...")
        try:
            resp = await client.post(f"{base_url}/assets/sync", headers=headers)
            print(f"状态码: {resp.status_code}")
            print(f"响应: {resp.text}")
        except Exception as e:
            print(f"错误: {e}")
            traceback.print_exc()

        # 测试发现 API
        print("\n3. 测试 /assets/discovery...")
        try:
            resp = await client.get(f"{base_url}/assets/discovery", headers=headers)
            print(f"状态码: {resp.status_code}")
            data = resp.json()
            print(f"发现节点总数: {data.get('total')}")
            print(f"未导入节点数: {data.get('discovered')}")
        except Exception as e:
            print(f"错误: {e}")
            traceback.print_exc()


if __name__ == '__main__':
    asyncio.run(test_sync())
