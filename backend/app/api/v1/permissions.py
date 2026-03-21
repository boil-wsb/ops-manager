"""
Permission management API routes.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.permissions import require_permissions
from app.crud.crud_permission import crud_permission
from app.models.user import User
from app.schemas.permission import PermissionModule, PermissionResponse

router = APIRouter(prefix="/permissions")

MODULE_NAMES = {
    "user": "用户管理",
    "role": "角色管理",
    "asset": "资产管理",
    "monitor": "监控管理",
    "alert": "告警管理",
    "deployment": "发布部署",
    "certificate": "证书管理",
    "setting": "系统设置",
}


@router.get("", response_model=dict)
async def list_permissions(
    module: Optional[str] = Query(None, description="Filter by module"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=1000, description="Page size"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get permission list with filters."""
    require_permissions(["role:read"])(current_user)

    skip = (page - 1) * page_size

    permissions, total = await crud_permission.get_multi_with_filters(
        db,
        module=module,
        is_active=is_active,
        skip=skip,
        limit=page_size,
    )

    module_groups = {}
    for perm in permissions:
        if perm.module not in module_groups:
            module_groups[perm.module] = {
                "module": perm.module,
                "module_name": MODULE_NAMES.get(perm.module, perm.module),
                "permissions": [],
            }
        module_groups[perm.module]["permissions"].append(
            PermissionResponse.model_validate(perm)
        )

    return {
        "items": list(module_groups.values()),
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/modules", response_model=list)
async def get_permission_modules(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all permission modules."""
    require_permissions(["role:read"])(current_user)

    modules = await crud_permission.get_modules(db)

    return [
        PermissionModule(
            code=module,
            name=MODULE_NAMES.get(module, module),
        )
        for module in modules
    ]


@router.get("/{permission_id}", response_model=PermissionResponse)
async def get_permission(
    permission_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get permission by ID."""
    require_permissions(["role:read"])(current_user)

    permission = await crud_permission.get(db, id=permission_id)

    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="权限不存在",
        )

    return permission
