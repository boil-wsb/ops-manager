"""
测试用户列表 API
"""
import asyncio
import httpx
import json


async def test_users():
    base_url = "http://localhost:8000/api/v1"

    async with httpx.AsyncClient(timeout=30.0) as client:
        print("测试用户列表 API...")

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

        # 获取用户列表
        print("\n2. 获取用户列表...")
        resp = await client.get(f"{base_url}/users", headers=headers)
        print(f"状态码: {resp.status_code}")
        print(f"响应: {json.dumps(resp.json(), indent=2, default=str)}")


if __name__ == '__main__':
    asyncio.run(test_users())
