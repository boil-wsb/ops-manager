"""
Role management API routes.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select

from app.api.deps import get_db, get_current_user
from app.crud.crud_role import crud_role
from app.crud.crud_permission import crud_permission
from app.schemas.permission import (
    RoleCreate,
    RoleUpdate,
    RoleResponse,
    RoleDetailResponse,
    RolePermissionUpdate,
    RolePermissionResponse,
    PermissionResponse,
)
from app.core.permissions import require_permissions
from app.models.permission import Role

router = APIRouter(prefix="/roles")


@router.get("", response_model=dict)
async def list_roles(
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
    _: None = Depends(require_permissions(["role:read"])),
):
    """Get role list with filters."""
    skip = (page - 1) * page_size
    
    roles, total = await crud_role.get_multi_with_filters(
        db,
        is_active=is_active,
        skip=skip,
        limit=page_size,
    )
    
    # Build response with counts
    items = []
    for role in roles:
        role_dict = {
            "id": role.id,
            "name": role.name,
            "description": role.description,
            "is_system": role.is_system,
            "is_active": role.is_active,
            "permission_count": len(role.permissions),
            "user_count": len(role.users),
            "created_at": role.created_at,
            "updated_at": role.updated_at,
        }
        items.append(role_dict)
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    role_in: RoleCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
    _: None = Depends(require_permissions(["role:create"])),
):
    """Create a new role."""
    # Check if role name already exists
    existing_role = await crud_role.get_by_name(db, name=role_in.name)
    if existing_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="角色名称已存在",
        )
    
    # Validate permission IDs
    if role_in.permission_ids:
        for perm_id in role_in.permission_ids:
            perm = await crud_permission.get(db, id=perm_id)
            if not perm:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"权限ID {perm_id} 不存在",
                )
    
    role = await crud_role.create_with_permissions(db, obj_in=role_in)
    
    return {
        "id": role.id,
        "name": role.name,
        "description": role.description,
        "is_system": role.is_system,
        "is_active": role.is_active,
        "permission_count": len(role.permissions),
        "user_count": 0,
        "created_at": role.created_at,
        "updated_at": role.updated_at,
    }


@router.get("/{role_id}", response_model=RoleDetailResponse)
async def get_role(
    role_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
    _: None = Depends(require_permissions(["role:read"])),
):
    """Get role by ID with permissions."""
    role = await crud_role.get(db, id=role_id)
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="角色不存在",
        )
    
    return {
        "id": role.id,
        "name": role.name,
        "description": role.description,
        "is_system": role.is_system,
        "is_active": role.is_active,
        "permissions": [
            PermissionResponse.model_validate(p) for p in role.permissions
        ],
        "created_at": role.created_at,
        "updated_at": role.updated_at,
    }


@router.put("/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: int,
    role_in: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
    _: None = Depends(require_permissions(["role:update"])),
):
    """Update a role."""
    role = await crud_role.get(db, id=role_id)
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="角色不存在",
        )
    
    # Prevent updating system roles
    if role.is_system:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="系统预设角色不能修改",
        )
    
    # Check name uniqueness if name is being updated
    if role_in.name and role_in.name != role.name:
        existing_role = await crud_role.get_by_name(db, name=role_in.name)
        if existing_role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="角色名称已存在",
            )
    
    role = await crud_role.update(db, db_obj=role, obj_in=role_in)
    
    return {
        "id": role.id,
        "name": role.name,
        "description": role.description,
        "is_system": role.is_system,
        "is_active": role.is_active,
        "permission_count": len(role.permissions),
        "user_count": len(role.users),
        "created_at": role.created_at,
        "updated_at": role.updated_at,
    }


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
    _: None = Depends(require_permissions(["role:delete"])),
):
    """Delete a role."""
    role = await crud_role.get(db, id=role_id)
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="角色不存在",
        )
    
    # Prevent deleting system roles
    if role.is_system:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="系统预设角色不能删除",
        )
    
    # Check if role has users
    if role.users:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该角色下还有用户，不能删除",
        )
    
    await crud_role.remove(db, id=role_id)
    return None


@router.get("/{role_id}/permissions", response_model=RolePermissionResponse)
async def get_role_permissions(
    role_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
    _: None = Depends(require_permissions(["role:read"])),
):
    """Get role permissions."""
    role = await crud_role.get(db, id=role_id)
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="角色不存在",
        )
    
    return {
        "role_id": role.id,
        "permissions": [
            PermissionResponse.model_validate(p) for p in role.permissions
        ],
        "permission_count": len(role.permissions),
    }


@router.put("/{role_id}/permissions", response_model=RolePermissionResponse)
async def update_role_permissions(
    role_id: int,
    perm_update: RolePermissionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
    _: None = Depends(require_permissions(["role:update"])),
):
    """Update role permissions."""
    role = await crud_role.get(db, id=role_id)
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="角色不存在",
        )
    
    # Validate permission IDs
    if perm_update.permission_ids:
        for perm_id in perm_update.permission_ids:
            perm = await crud_permission.get(db, id=perm_id)
            if not perm:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"权限ID {perm_id} 不存在",
                )
    
    role = await crud_role.update_permissions(
        db, role=role, permission_ids=perm_update.permission_ids
    )
    
    return {
        "role_id": role.id,
        "permissions": [
            PermissionResponse.model_validate(p) for p in role.permissions
        ],
        "permission_count": len(role.permissions),
    }
