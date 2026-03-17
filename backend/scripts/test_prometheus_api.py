"""
测试 Prometheus 相关 API
"""
import asyncio
import httpx


async def test_prometheus_api():
    base_url = "http://localhost:8000/api/v1"

    async with httpx.AsyncClient() as client:
        print("=" * 60)
        print("测试 Prometheus 相关 API")
        print("=" * 60)

        # 登录
        print("\n1. 登录...")
        try:
            login_resp = await client.post(
                f"{base_url}/auth/login",
                json={"username": "admin", "password": "admin123"}
            )
            if login_resp.status_code == 200:
                token = login_resp.json()["access_token"]
                print("   登录成功")
            else:
                print(f"   登录失败: {login_resp.status_code}")
                print(f"   响应: {login_resp.text}")
                return
        except Exception as e:
            print(f"   错误: {e}")
            return

        headers = {"Authorization": f"Bearer {token}"}

        # 测试资产发现 API
        print("\n2. 资产发现 API...")
        try:
            resp = await client.get(f"{base_url}/assets/discovery", headers=headers)
            print(f"   状态码: {resp.status_code}")
            print(f"   响应: {resp.text[:500]}")
        except Exception as e:
            print(f"   错误: {e}")
            import traceback
            traceback.print_exc()

        # 测试手动同步 API
        print("\n3. 手动同步 API...")
        try:
            resp = await client.post(f"{base_url}/assets/sync", headers=headers)
            print(f"   状态码: {resp.status_code}")
            print(f"   响应: {resp.text[:500]}")
        except Exception as e:
            print(f"   错误: {e}")
            import traceback
            traceback.print_exc()

        print("\n" + "=" * 60)


if __name__ == '__main__':
    asyncio.run(test_prometheus_api())
