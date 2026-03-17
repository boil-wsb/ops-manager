"""
完整检查 API 响应
"""
import asyncio
import httpx


async def check_api():
    base_url = "http://localhost:8000/api/v1"
    
    async with httpx.AsyncClient() as client:
        print("=" * 60)
        print("完整 API 检查")
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
                print(f"   登录成功")
                print(f"   Token: {token[:30]}...")
            else:
                print(f"   登录失败: {login_resp.text}")
                return
        except Exception as e:
            print(f"   错误: {e}")
            return
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # 检查用户列表 API
        print("\n2. 用户列表 API...")
        try:
            resp = await client.get(f"{base_url}/users", headers=headers)
            print(f"   状态码: {resp.status_code}")
            data = resp.json()
            print(f"   响应键: {list(data.keys())}")
            
            if "data" in data:
                inner = data["data"]
                print(f"   data 键: {list(inner.keys()) if isinstance(inner, dict) else 'not dict'}")
                if isinstance(inner, dict) and "items" in inner:
                    print(f"   用户数量: {len(inner['items'])}")
                    if inner['items']:
                        user = inner['items'][0]
                        print(f"   第一个用户字段: {list(user.keys())}")
            elif "items" in data:
                print(f"   用户数量: {len(data['items'])}")
            else:
                print(f"   响应内容: {str(data)[:200]}")
        except Exception as e:
            print(f"   错误: {e}")
        
        # 检查资产列表 API
        print("\n3. 资产列表 API...")
        try:
            resp = await client.get(f"{base_url}/assets", headers=headers)
            print(f"   状态码: {resp.status_code}")
            data = resp.json()
            print(f"   响应键: {list(data.keys())}")
            
            if "data" in data:
                inner = data["data"]
                print(f"   data 键: {list(inner.keys()) if isinstance(inner, dict) else 'not dict'}")
                if isinstance(inner, dict) and "items" in inner:
                    print(f"   资产数量: {len(inner['items'])}")
            elif "items" in data:
                print(f"   资产数量: {len(data['items'])}")
            else:
                print(f"   响应内容: {str(data)[:200]}")
        except Exception as e:
            print(f"   错误: {e}")
        
        # 检查告警列表 API
        print("\n4. 告警列表 API...")
        try:
            resp = await client.get(f"{base_url}/alerts", headers=headers)
            print(f"   状态码: {resp.status_code}")
            data = resp.json()
            print(f"   响应键: {list(data.keys())}")
            
            if "data" in data:
                inner = data["data"]
                print(f"   data 键: {list(inner.keys()) if isinstance(inner, dict) else 'not dict'}")
                if isinstance(inner, dict) and "items" in inner:
                    print(f"   告警数量: {len(inner['items'])}")
            elif "items" in data:
                print(f"   告警数量: {len(data['items'])}")
            else:
                print(f"   响应内容: {str(data)[:200]}")
        except Exception as e:
            print(f"   错误: {e}")
        
        print("\n" + "=" * 60)


if __name__ == '__main__':
    asyncio.run(check_api())
