"""
检查用户数据，包括 last_login 字段
"""
import asyncio
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.user import User


async def check_user_data():
    async with AsyncSessionLocal() as db:
        print("=" * 60)
        print("用户数据检查")
        print("=" * 60)
        
        result = await db.execute(
            select(User).order_by(User.id)
        )
        users = result.scalars().all()
        
        print(f"\n总共有 {len(users)} 个用户\n")
        
        for user in users:
            print(f"用户: {user.username}")
            print(f"  ID: {user.id}")
            print(f"  邮箱: {user.email}")
            print(f"  全名: {user.full_name}")
            print(f"  是否激活: {user.is_active}")
            print(f"  是否超级用户: {user.is_superuser}")
            print(f"  最后登录: {user.last_login}")
            print(f"  创建时间: {user.created_at}")
            print(f"  更新时间: {user.updated_at}")
            print()


if __name__ == '__main__':
    asyncio.run(check_user_data())
