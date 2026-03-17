"""
简单测试用户列表 API
"""
import asyncio
import httpx


async def test_users_api():
    async with httpx.AsyncClient() as client:
        # 登录
        login_resp = await client.post(
            "http://localhost:8000/api/v1/auth/login",
            json={"username": "admin", "password": "admin123"}
        )
        
        if login_resp.status_code != 200:
            print(f"登录失败: {login_resp.status_code}")
            return
        
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 获取用户列表
        users_resp = await client.get(
            "http://localhost:8000/api/v1/users",
            headers=headers
        )
        
        print(f"状态码: {users_resp.status_code}")
        print(f"响应内容: {users_resp.text[:500]}")


if __name__ == '__main__':
    asyncio.run(test_users_api())
