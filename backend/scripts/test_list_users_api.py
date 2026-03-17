"""
测试用户列表 API
"""
import asyncio
from sqlalchemy import select, func
from app.db.session import AsyncSessionLocal
from app.models.user import User


async def test_list_users():
    async with AsyncSessionLocal() as db:
        print("=" * 60)
        print("测试用户列表 API 逻辑")
        print("=" * 60)
        
        # 模拟 API 查询
        query = select(User).order_by(User.id)
        
        # 获取总数
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        print(f"\n总用户数: {total}")
        
        # 获取用户列表
        result = await db.execute(query)
        users = result.scalars().all()
        
        # 构建响应数据
        items = []
        for u in users:
            user_data = {
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "full_name": u.full_name,
                "is_active": u.is_active,
                "is_superuser": u.is_superuser,
                "last_login": u.last_login.isoformat() if u.last_login else None,
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "updated_at": u.updated_at.isoformat() if u.updated_at else None,
            }
            items.append(user_data)
            print(f"\n用户: {u.username}")
            print(f"  full_name: {user_data['full_name']}")
            print(f"  is_active: {user_data['is_active']}")
            print(f"  is_superuser: {user_data['is_superuser']}")
        
        response = {
            "items": items,
            "total": total,
        }
        
        print("\n" + "=" * 60)
        print("API 响应结构:")
        print(f"  items: {len(response['items'])} 个用户")
        print(f"  total: {response['total']}")
        print("=" * 60)


if __name__ == '__main__':
    asyncio.run(test_list_users())
