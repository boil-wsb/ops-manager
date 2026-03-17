"""
Role CRUD operations.
"""
from typing import Optional, List, Tuple

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.permission import Role, Permission
from app.schemas.permission import RoleCreate, RoleUpdate


class CRUDRole(CRUDBase[Role, RoleCreate, RoleUpdate]):
    """Role CRUD operations."""
    
    async def get_by_name(
        self,
        db: AsyncSession,
        *,
        name: str
    ) -> Optional[Role]:
        """Get role by name."""
        result = await db.execute(
            select(Role).where(Role.name == name)
        )
        return result.scalar_one_or_none()
    
    async def get_multi_with_filters(
        self,
        db: AsyncSession,
        *,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[Role], int]:
        """Get roles with filters and total count."""
        query = select(Role)
        count_query = select(func.count(Role.id))
        
        # Apply filters
        if is_active is not None:
            query = query.where(Role.is_active == is_active)
            count_query = count_query.where(Role.is_active == is_active)
        
        # Execute count query
        count_result = await db.execute(count_query)
        total = count_result.scalar()
        
        # Execute main query
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        roles = result.scalars().all()
        
        return list(roles), total
    
    async def create_with_permissions(
        self,
        db: AsyncSession,
        *,
        obj_in: RoleCreate
    ) -> Role:
        """Create a new role with permissions."""
        # Extract permission_ids
        permission_ids = obj_in.permission_ids
        role_data = obj_in.model_dump(exclude={"permission_ids"})
        
        # Create role
        db_obj = Role(**role_data)
        db.add(db_obj)
        await db.flush()  # Flush to get the role ID
        
        # Add permissions if provided
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
        self,
        db: AsyncSession,
        *,
        role: Role,
        permission_ids: List[int]
    ) -> Role:
        """Update role permissions."""
        # Clear existing permissions
        role.permissions = []
        
        # Add new permissions
        if permission_ids:
            permissions_result = await db.execute(
                select(Permission).where(Permission.id.in_(permission_ids))
            )
            permissions = permissions_result.scalars().all()
            role.permissions.extend(permissions)
        
        await db.commit()
        await db.refresh(role)
        return role
    
    async def get_permission_ids(
        self,
        db: AsyncSession,
        *,
        role_id: int
    ) -> List[int]:
        """Get permission IDs for a role."""
        result = await db.execute(
            select(Role).where(Role.id == role_id)
        )
        role = result.scalar_one_or_none()
        
        if not role:
            return []
        
        return [p.id for p in role.permissions]


crud_role = CRUDRole(Role)
