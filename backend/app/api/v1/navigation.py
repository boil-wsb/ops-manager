"""
Navigation link management API routes.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_current_user_optional, get_db
from app.core.audit import audit_log
from app.core.permissions import require_permissions
from app.crud.crud_navigation import navigation_link
from app.models.permission import Role
from app.models.user import User
from app.schemas.navigation import (
    NavigationLinkCreate,
    NavigationLinkResponse,
    NavigationLinkUpdate,
)

router = APIRouter(prefix="/navigation")
logger = logging.getLogger(__name__)


@router.get("/public", response_model=dict)
async def get_public_navigation_links(
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    """Get active navigation links grouped by category, filtered by user roles."""
    if current_user and not current_user.is_superuser:
        user_role_ids = {role.id for role in current_user.roles}
        grouped = await navigation_link.get_grouped_links_for_user(db, user_role_ids)
    else:
        grouped = await navigation_link.get_grouped_links(db)

    result = []
    for category, links in grouped.items():
        result.append({
            "category": category,
            "links": [NavigationLinkResponse.model_validate(link) for link in links],
        })
    return {"groups": result}


@router.get("", response_model=dict)
async def list_navigation_links(
    category: str | None = Query(None, description="Filter by category"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get navigation link list with filters.

    For non-superadmin users, only shows records where:
    - The roles list is empty (public to all roles)
    - OR the user's role is in the navigation link's roles list
    """
    require_permissions(["navigation:read"])(current_user)

    skip = (page - 1) * page_size

    is_superadmin = current_user.is_superuser
    user_role_ids = [role.id for role in current_user.roles] if current_user.roles else []

    links = await navigation_link.get_multi_with_access_filter(
        db,
        category=category,
        is_active=is_active,
        skip=skip,
        limit=page_size,
        is_superadmin=is_superadmin,
        user_role_ids=user_role_ids,
    )

    total = await navigation_link.count_with_access_filter(
        db,
        category=category,
        is_active=is_active,
        is_superadmin=is_superadmin,
        user_role_ids=user_role_ids,
    )

    return {
        "items": [NavigationLinkResponse.model_validate(link) for link in links],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("", response_model=NavigationLinkResponse, status_code=status.HTTP_201_CREATED)
@audit_log(operation_type="CREATE", module="navigation", object_type="NavigationLink")
async def create_navigation_link(
    request: Request,
    link_in: NavigationLinkCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new navigation link."""
    require_permissions(["navigation:create"])(current_user)
    logger.info(f"[导航管理] 创建导航链接 '{link_in.name}'")

    role_ids = None
    if link_in.restrict_to_current_role and current_user.roles:
        role_ids = [role.id for role in current_user.roles]

    link = await navigation_link.create_with_roles(db, obj_in=link_in, role_ids=role_ids)
    logger.info(f"[导航管理] 导航链接 '{link.name}' 创建成功，ID: {link.id}")

    return NavigationLinkResponse.model_validate(link)


@router.get("/{link_id}", response_model=NavigationLinkResponse)
async def get_navigation_link(
    link_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get navigation link by ID."""
    require_permissions(["navigation:read"])(current_user)

    link = await navigation_link.get_with_roles(db, id=link_id)

    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="导航链接不存在",
        )

    return NavigationLinkResponse.model_validate(link)


@router.put("/{link_id}", response_model=NavigationLinkResponse)
@audit_log(operation_type="UPDATE", module="navigation", object_type="NavigationLink")
async def update_navigation_link(
    request: Request,
    link_id: int,
    link_in: NavigationLinkUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a navigation link."""
    require_permissions(["navigation:update"])(current_user)

    link = await navigation_link.get_with_roles(db, id=link_id)

    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="导航链接不存在",
        )

    role_ids = None
    if link_in.restrict_to_current_role is not None:
        if link_in.restrict_to_current_role:
            if current_user.is_superuser:
                role_result = await db.execute(
                    select(Role).where(Role.name == "superadmin")
                )
                superadmin_role = role_result.scalar_one_or_none()
                role_ids = [superadmin_role.id] if superadmin_role else []
            elif not current_user.roles:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="当前用户没有关联角色，无法设置可见范围为当前角色，请先为用户分配角色",
                )
            else:
                role_ids = [role.id for role in current_user.roles]
        else:
            role_ids = []

    link = await navigation_link.update_with_roles(db, db_obj=link, obj_in=link_in, role_ids=role_ids)
    logger.info(f"[导航管理] 导航链接 '{link.name}' 更新成功")

    return NavigationLinkResponse.model_validate(link)


@router.delete("/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
@audit_log(operation_type="DELETE", module="navigation", object_type="NavigationLink")
async def delete_navigation_link(
    request: Request,
    link_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a navigation link."""
    require_permissions(["navigation:delete"])(current_user)

    link = await navigation_link.get(db, id=link_id)

    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="导航链接不存在",
        )

    await navigation_link.delete(db, id=link_id)
    logger.info(f"[导航管理] 导航链接 ID={link_id} 删除成功")

    return None
