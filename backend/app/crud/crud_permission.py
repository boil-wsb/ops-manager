"""
Permission CRUD operations.
"""
from typing import Optional, List, Tuple

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.permission import Permission
from app.schemas.permission import PermissionCreate, PermissionUpdate


class CRUDPermission(CRUDBase[Permission, PermissionCreate, PermissionUpdate]):
    """Permission CRUD operations."""
    
    async def get_by_code(
        self,
        db: AsyncSession,
        *,
        code: str
    ) -> Optional[Permission]:
        """Get permission by code."""
        result = await db.execute(
            select(Permission).where(Permission.code == code)
        )
        return result.scalar_one_or_none()
    
    async def get_by_module(
        self,
        db: AsyncSession,
        *,
        module: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Permission]:
        """Get permissions by module."""
        result = await db.execute(
            select(Permission)
            .where(Permission.module == module)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
    
    async def get_active_permissions(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100
    ) -> List[Permission]:
        """Get active permissions."""
        result = await db.execute(
            select(Permission)
            .where(Permission.is_active == True)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
    
    async def get_modules(self, db: AsyncSession) -> List[str]:
        """Get all distinct permission modules."""
        result = await db.execute(
            select(Permission.module).distinct()
        )
        return result.scalars().all()
    
    async def get_multi_with_filters(
        self,
        db: AsyncSession,
        *,
        module: Optional[str] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[Permission], int]:
        """Get permissions with filters and total count."""
        query = select(Permission)
        count_query = select(func.count(Permission.id))
        
        # Apply filters
        if module:
            query = query.where(Permission.module == module)
            count_query = count_query.where(Permission.module == module)
        
        if is_active is not None:
            query = query.where(Permission.is_active == is_active)
            count_query = count_query.where(Permission.is_active == is_active)
        
        # Execute count query
        count_result = await db.execute(count_query)
        total = count_result.scalar()
        
        # Execute main query
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        permissions = result.scalars().all()
        
        return list(permissions), total


crud_permission = CRUDPermission(Permission)
