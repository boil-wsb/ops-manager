"""
Role management API routes.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.audit import audit_log
from app.core.cache import cache_delete_pattern, cache_get_or_set
from app.core.logging import get_logger
from app.core.permissions import require_permissions
from app.crud.crud_role import crud_role
from app.models.permission import Permission
from app.models.user import User
from app.schemas.permission import (
    PermissionResponse,
    RoleCreate,
    RoleDetailResponse,
    RolePermissionResponse,
    RolePermissionUpdate,
    RoleResponse,
    RoleUpdate,
)

router = APIRouter(prefix="/roles")
logger = get_logger(__name__)


@router.get("", response_model=dict)
async def list_roles(
    is_active: bool | None = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get role list with filters."""
    require_permissions(["role:read"])(current_user)

    skip = (page - 1) * page_size

    cache_key = f"roles:list:{is_active}:{page}:{page_size}"

    async def _fetch_roles():
        roles, total = await crud_role.get_multi_with_filters(
            db,
            is_active=is_active,
            skip=skip,
            limit=page_size,
        )
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
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    return await cache_get_or_set(cache_key, _fetch_roles, ttl=120)


@router.post("", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
@audit_log(operation_type="CREATE", module="role", object_type="Role")
async def create_role(
    request: Request,
    role_in: RoleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建新角色"""
    require_permissions(["role:create"])(current_user)
    logger.info(
        f"创建角色 '{role_in.name}'", extra={"action": "role.create", "role_name": role_in.name}
    )

    existing_role = await crud_role.get_by_name(db, name=role_in.name)
    if existing_role:
        logger.warning(
            f"角色名称 '{role_in.name}' 已存在",
            extra={"action": "role.create", "role_name": role_in.name},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="角色名称已存在",
        )

    if role_in.permission_ids:
        perms_result = await db.execute(
            select(Permission).where(Permission.id.in_(role_in.permission_ids))
        )
        found_ids = {p.id for p in perms_result.scalars().all()}
        missing_ids = set(role_in.permission_ids) - found_ids
        if missing_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"权限ID {', '.join(str(i) for i in missing_ids)} 不存在",
            )

    role = await crud_role.create_with_permissions(db, obj_in=role_in)
    logger.info(
        f"角色 '{role.name}' 创建成功，ID: {role.id}",
        extra={"action": "role.create", "role_name": role.name, "role_id": role.id},
    )

    await cache_delete_pattern("roles:list:*")

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
    current_user: User = Depends(get_current_user),
):
    """Get role by ID with permissions."""
    require_permissions(["role:read"])(current_user)

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
        "permissions": [PermissionResponse.model_validate(p) for p in role.permissions],
        "created_at": role.created_at,
        "updated_at": role.updated_at,
    }


@router.put("/{role_id}", response_model=RoleResponse)
@audit_log(operation_type="UPDATE", module="role", object_type="Role")
async def update_role(
    request: Request,
    role_id: int,
    role_in: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a role."""
    require_permissions(["role:update"])(current_user)

    role = await crud_role.get(db, id=role_id)

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="角色不存在",
        )

    if role.is_system:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="系统预设角色不能修改",
        )

    if role_in.name and role_in.name != role.name:
        existing_role = await crud_role.get_by_name(db, name=role_in.name)
        if existing_role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="角色名称已存在",
            )

    role = await crud_role.update(db, db_obj=role, obj_in=role_in)

    await cache_delete_pattern("roles:list:*")

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
@audit_log(operation_type="DELETE", module="role", object_type="Role")
async def delete_role(
    request: Request,
    role_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a role."""
    require_permissions(["role:delete"])(current_user)

    role = await crud_role.get(db, id=role_id)

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="角色不存在",
        )

    if role.is_system:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="系统预设角色不能删除",
        )

    if role.users:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该角色下还有用户，不能删除",
        )

    await crud_role.delete(db, id=role_id)
    await cache_delete_pattern("roles:list:*")
    return None


@router.get("/{role_id}/permissions", response_model=RolePermissionResponse)
async def get_role_permissions(
    role_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get role permissions."""
    require_permissions(["role:read"])(current_user)

    role = await crud_role.get(db, id=role_id)

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="角色不存在",
        )

    return {
        "role_id": role.id,
        "permissions": [PermissionResponse.model_validate(p) for p in role.permissions],
        "permission_count": len(role.permissions),
    }


@router.put("/{role_id}/permissions", response_model=RolePermissionResponse)
@audit_log(operation_type="ASSIGN_PERMISSION", module="role", object_type="Role")
async def update_role_permissions(
    request: Request,
    role_id: int,
    perm_update: RolePermissionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新角色权限"""
    require_permissions(["role:update"])(current_user)
    logger.info(
        f"更新角色 ID={role_id} 的权限", extra={"action": "role.update", "role_id": role_id}
    )

    role = await crud_role.get(db, id=role_id)

    if not role:
        logger.warning(
            f"角色 ID={role_id} 不存在", extra={"action": "role.update", "role_id": role_id}
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="角色不存在",
        )

    old_perm_count = len(role.permissions)

    if perm_update.permission_ids:
        perms_result = await db.execute(
            select(Permission).where(Permission.id.in_(perm_update.permission_ids))
        )
        found_ids = {p.id for p in perms_result.scalars().all()}
        missing_ids = set(perm_update.permission_ids) - found_ids
        if missing_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"权限ID {', '.join(str(i) for i in missing_ids)} 不存在",
            )

    role = await crud_role.update_permissions(
        db, role=role, permission_ids=perm_update.permission_ids
    )

    logger.info(
        f"角色 '{role.name}' 权限更新成功: {old_perm_count} -> {len(role.permissions)} 个权限",
        extra={
            "action": "role.update",
            "role_name": role.name,
            "role_id": role.id,
            "old_count": old_perm_count,
            "new_count": len(role.permissions),
        },
    )

    await cache_delete_pattern("roles:list:*")

    return {
        "role_id": role.id,
        "permissions": [PermissionResponse.model_validate(p) for p in role.permissions],
        "permission_count": len(role.permissions),
    }
