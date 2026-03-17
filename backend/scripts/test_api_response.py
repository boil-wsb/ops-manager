"""
测试 API 响应格式
"""
import asyncio
from sqlalchemy import select, func
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.schemas.user import UserResponse
from app.api.responses import api_response


async def test_api_response():
    async with AsyncSessionLocal() as db:
        print("=" * 60)
        print("测试 API 响应格式")
        print("=" * 60)
        
        query = select(User).order_by(User.id)
        
        # 获取总数
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # 获取用户列表
        result = await db.execute(query)
        users = result.scalars().all()
        
        # 构建 API 响应（与后端 API 完全一致）
        response_data = {
            "items": [UserResponse.model_validate({
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "full_name": u.full_name,
                "is_active": u.is_active,
                "is_superuser": u.is_superuser,
                "last_login": u.last_login,
                "created_at": u.created_at,
                "updated_at": u.updated_at,
                "permissions": [],
            }) for u in users],
            "total": total,
            "page": 1,
            "page_size": 20,
        }
        
        # 使用 api_response 包装
        response = api_response(data=response_data)
        
        print("\nAPI 响应结构:")
        print(f"  code: {response['code']}")
        print(f"  message: {response['message']}")
        print(f"  data.total: {response['data']['total']}")
        print(f"  data.items: {len(response['data']['items'])} 个用户")
        
        print("\n第一个用户数据:")
        if response['data']['items']:
            first_user = response['data']['items'][0]
            print(f"  id: {first_user.id}")
            print(f"  username: {first_user.username}")
            print(f"  email: {first_user.email}")
            print(f"  full_name: {first_user.full_name}")
            print(f"  is_active: {first_user.is_active}")
            print(f"  is_superuser: {first_user.is_superuser}")
            print(f"  last_login: {first_user.last_login}")
        
        print("\n" + "=" * 60)


if __name__ == '__main__':
    asyncio.run(test_api_response())
