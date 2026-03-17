"""
测试用户列表 API 返回的数据
"""
import asyncio
import json
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.schemas.user import UserResponse


async def test_user_api():
    async with AsyncSessionLocal() as db:
        print("=" * 60)
        print("测试用户列表 API 返回数据")
        print("=" * 60)
        
        query = select(User).order_by(User.id)
        result = await db.execute(query)
        users = result.scalars().all()
        
        print(f"\n查询到 {len(users)} 个用户\n")
        
        for user in users:
            print(f"\n用户: {user.username}")
            print(f"  原始 last_login: {user.last_login}")
            print(f"  类型: {type(user.last_login)}")
            
            # 模拟 API 返回的数据
            user_data = {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "is_active": user.is_active,
                "is_superuser": user.is_superuser,
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "updated_at": user.updated_at.isoformat() if user.updated_at else None,
                "permissions": [],
            }
            
            print(f"  API 返回 last_login: {user_data['last_login']}")
            
            # 使用 Pydantic 模型验证
            try:
                validated = UserResponse.model_validate(user_data)
                print(f"  Pydantic 验证后 last_login: {validated.last_login}")
            except Exception as e:
                print(f"  Pydantic 验证错误: {e}")


if __name__ == '__main__':
    asyncio.run(test_user_api())
