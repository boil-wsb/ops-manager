"""
添加 asset:admin 权限到数据库
"""

import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.permission import Permission, Role


async def add_asset_admin_permission():
    async with AsyncSessionLocal() as db:
        # 检查权限是否已存在
        result = await db.execute(select(Permission).where(Permission.code == "asset:admin"))
        existing = result.scalar_one_or_none()

        if existing:
            print("asset:admin 权限已存在")
        else:
            # 创建新权限
            permission = Permission(
                code="asset:admin",
                name="资产管理",
                module="asset",
                action="admin",
                description="管理资产同步等高级操作",
                is_active=True,
            )
            db.add(permission)
            await db.commit()
            print("asset:admin 权限已创建")

        # 将权限分配给 admin 角色
        result = await db.execute(select(Role).where(Role.name == "admin"))
        admin_role = result.scalar_one_or_none()

        if admin_role:
            result = await db.execute(select(Permission).where(Permission.code == "asset:admin"))
            asset_admin_perm = result.scalar_one_or_none()

            if asset_admin_perm and asset_admin_perm not in admin_role.permissions:
                admin_role.permissions.append(asset_admin_perm)
                await db.commit()
                print("asset:admin 权限已分配给 admin 角色")
            else:
                print("admin 角色已有 asset:admin 权限")
        else:
            print("未找到 admin 角色")


if __name__ == "__main__":
    asyncio.run(add_asset_admin_permission())
