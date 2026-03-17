"""
检查当前权限分配情况
"""
import asyncio
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.permission import Permission, Role


async def check_permissions():
    async with AsyncSessionLocal() as db:
        print("=" * 60)
        print("权限检查报告")
        print("=" * 60)
        
        # 1. 检查所有权限
        print("\n1. 数据库中的所有权限:")
        result = await db.execute(select(Permission).order_by(Permission.code))
        permissions = result.scalars().all()
        for perm in permissions:
            print(f"   - {perm.code}: {perm.name} ({perm.module}/{perm.action})")
        
        # 2. 检查 asset:admin 权限是否存在
        print("\n2. asset:admin 权限检查:")
        result = await db.execute(
            select(Permission).where(Permission.code == "asset:admin")
        )
        asset_admin = result.scalar_one_or_none()
        if asset_admin:
            print(f"   ✓ asset:admin 权限存在 (ID: {asset_admin.id})")
            print(f"     名称: {asset_admin.name}")
            print(f"     模块: {asset_admin.module}")
            print(f"     动作: {asset_admin.action}")
        else:
            print("   ✗ asset:admin 权限不存在")
        
        # 3. 检查所有角色及其权限
        print("\n3. 角色权限分配:")
        result = await db.execute(select(Role).order_by(Role.name))
        roles = result.scalars().all()
        
        for role in roles:
            print(f"\n   角色: {role.name} ({role.description})")
            role_perms = [p.code for p in role.permissions]
            print(f"   权限数量: {len(role_perms)}")
            
            if "asset:admin" in role_perms:
                print(f"   ✓ 有 asset:admin 权限")
            else:
                print(f"   ✗ 无 asset:admin 权限")
            
            # 显示所有 asset 相关权限
            asset_perms = [p for p in role_perms if p.startswith("asset:")]
            if asset_perms:
                print(f"   Asset 权限: {', '.join(asset_perms)}")
        
        # 4. 检查 admin 用户
        print("\n4. Admin 用户检查:")
        from app.models.user import User
        result = await db.execute(
            select(User).where(User.username == "admin")
        )
        admin_user = result.scalar_one_or_none()
        
        if admin_user:
            print(f"   用户: {admin_user.username}")
            print(f"   超级用户: {admin_user.is_superuser}")
            print(f"   角色: {[r.name for r in admin_user.roles]}")
            
            # 收集所有权限
            all_perms = set()
            for role in admin_user.roles:
                for perm in role.permissions:
                    all_perms.add(perm.code)
            
            print(f"   总权限数: {len(all_perms)}")
            
            if "asset:admin" in all_perms:
                print(f"   ✓ 用户有 asset:admin 权限")
            else:
                print(f"   ✗ 用户无 asset:admin 权限")
        else:
            print("   ✗ 未找到 admin 用户")
        
        print("\n" + "=" * 60)


if __name__ == '__main__':
    asyncio.run(check_permissions())
