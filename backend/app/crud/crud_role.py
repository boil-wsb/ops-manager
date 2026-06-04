"""
Role CRUD operations.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase
from app.models.permission import Permission, Role, role_permissions
from app.schemas.permission import RoleCreate, RoleUpdate


class CRUDRole(CRUDBase[Role, RoleCreate, RoleUpdate]):
    """Role CRUD operations."""

    async def get_by_name(self, db: AsyncSession, *, name: str) -> Role | None:
        """Get role by name."""
        result = await db.execute(select(Role).where(Role.name == name))
        return result.scalar_one_or_none()

    async def get_multi_with_filters(
        self, db: AsyncSession, *, is_active: bool | None = None, skip: int = 0, limit: int = 100
    ) -> tuple[list[Role], int]:
        """Get roles with filters and total count."""
        query = select(Role).options(
            selectinload(Role.permissions),
            selectinload(Role.users),
        )
        count_query = select(func.count(Role.id))

        if is_active is not None:
            query = query.where(Role.is_active == is_active)
            count_query = count_query.where(Role.is_active == is_active)

        count_result = await db.execute(count_query)
        total = count_result.scalar()

        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        roles = result.scalars().all()

        return list(roles), total

    async def create_with_permissions(self, db: AsyncSession, *, obj_in: RoleCreate) -> Role:
        """Create a new role with permissions."""
        permission_ids = obj_in.permission_ids
        role_data = obj_in.model_dump(exclude={"permission_ids"})

        db_obj = Role(**role_data)
        db.add(db_obj)
        await db.flush()

        if permission_ids:
            permissions_result = await db.execute(
                select(Permission).where(Permission.id.in_(permission_ids))
            )
            permissions = permissions_result.scalars().all()
            db_obj.permissions.extend(permissions)

        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update_permissions(
        self, db: AsyncSession, *, role: Role, permission_ids: list[int]
    ) -> Role:
        """Update role permissions."""
        role.permissions = []

        if permission_ids:
            permissions_result = await db.execute(
                select(Permission).where(Permission.id.in_(permission_ids))
            )
            permissions = permissions_result.scalars().all()
            role.permissions.extend(permissions)

        await db.commit()
        await db.refresh(role)
        return role

    async def get_permission_ids(self, db: AsyncSession, *, role_id: int) -> list[int]:
        """Get permission IDs for a role."""
        result = await db.execute(
            select(role_permissions.c.permission_id).where(role_permissions.c.role_id == role_id)
        )
        return list(result.scalars().all())


crud_role = CRUDRole(Role)
