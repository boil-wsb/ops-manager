"""
直接测试 API 端点
"""
import asyncio
import httpx


async def test_api():
    base_url = "http://localhost:8000/api/v1"
    
    # 先登录获取 token
    async with httpx.AsyncClient() as client:
        print("=" * 60)
        print("测试 API 端点")
        print("=" * 60)
        
        # 登录
        print("\n1. 登录...")
        try:
            login_resp = await client.post(
                f"{base_url}/auth/login",
                json={"username": "admin", "password": "admin123"}
            )
            print(f"   状态码: {login_resp.status_code}")
            if login_resp.status_code == 200:
                login_data = login_resp.json()
                token = login_data.get("access_token")
                print(f"   登录成功，获取到 token")
            else:
                print(f"   登录失败: {login_resp.text}")
                return
        except Exception as e:
            print(f"   登录错误: {e}")
            return
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # 测试用户列表 API
        print("\n2. 测试用户列表 API...")
        try:
            users_resp = await client.get(
                f"{base_url}/users",
                headers=headers
            )
            print(f"   状态码: {users_resp.status_code}")
            if users_resp.status_code == 200:
                users_data = users_resp.json()
                print(f"   响应结构: {list(users_data.keys())}")
                if "items" in users_data:
                    print(f"   用户数量: {len(users_data['items'])}")
                    if users_data['items']:
                        print(f"   第一个用户: {users_data['items'][0].get('username')}")
                elif "data" in users_data:
                    print(f"   注意: 响应被包装在 data 字段中")
                    print(f"   用户数量: {len(users_data['data'].get('items', []))}")
                else:
                    print(f"   响应内容: {users_data}")
            else:
                print(f"   请求失败: {users_resp.text}")
        except Exception as e:
            print(f"   请求错误: {e}")
        
        # 测试资产列表 API
        print("\n3. 测试资产列表 API...")
        try:
            assets_resp = await client.get(
                f"{base_url}/assets",
                headers=headers
            )
            print(f"   状态码: {assets_resp.status_code}")
            if assets_resp.status_code == 200:
                assets_data = assets_resp.json()
                print(f"   响应结构: {list(assets_data.keys())}")
                if "items" in assets_data:
                    print(f"   资产数量: {len(assets_data['items'])}")
                elif "data" in assets_data:
                    print(f"   注意: 响应被包装在 data 字段中")
                    print(f"   资产数量: {len(assets_data['data'].get('items', []))}")
                else:
                    print(f"   响应内容: {assets_data}")
            else:
                print(f"   请求失败: {assets_resp.text}")
        except Exception as e:
            print(f"   请求错误: {e}")
        
        print("\n" + "=" * 60)


if __name__ == '__main__':
    asyncio.run(test_api())
