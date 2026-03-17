"""
测试资产列表 - 查看详细响应
"""
import asyncio
import httpx
import json


async def test_list_assets():
    base_url = "http://localhost:8000/api/v1"

    async with httpx.AsyncClient(timeout=30.0) as client:
        print("测试资产列表 API...")

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

        # 获取资产列表
        print("\n2. 获取资产列表...")
        resp = await client.get(f"{base_url}/assets", headers=headers)
        print(f"状态码: {resp.status_code}")

        if resp.status_code == 200:
            data = resp.json()
            print(f"\n完整响应:")
            print(json.dumps(data, indent=2, default=str))
        else:
            print(f"响应: {resp.text}")


if __name__ == '__main__':
    asyncio.run(test_list_assets())
