"""
Notification group management API routes.
"""

from app.core.logging import get_logger

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.audit import audit_log
from app.core.permissions import require_permissions
from app.crud.crud_notification_group import notification_group
from app.crud.crud_user import crud_user
from app.models.user import User
from app.schemas.notification_group import (
    NotificationGroupCreate,
    NotificationGroupResponse,
    NotificationGroupUpdate,
)

router = APIRouter(prefix="/notification-groups")
logger = get_logger(__name__)


@router.get("", response_model=dict)
async def list_notification_groups(
    notification_type: str | None = Query(None, description="Filter by notification type"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get notification group list with filters."""
    require_permissions(["notification_group:read"])(current_user)

    skip = (page - 1) * page_size

    groups = await notification_group.get_multi_with_filter(
        db,
        notification_type=notification_type,
        is_active=is_active,
        skip=skip,
        limit=page_size,
    )

    total = await notification_group.count_with_filter(
        db,
        notification_type=notification_type,
        is_active=is_active,
    )

    return {
        "items": [NotificationGroupResponse.model_validate(g) for g in groups],
        "total": total,
    }


@router.post("", response_model=NotificationGroupResponse, status_code=status.HTTP_201_CREATED)
@audit_log(operation_type="CREATE", module="notification_group", object_type="NotificationGroup")
async def create_notification_group(
    request: Request,
    group_in: NotificationGroupCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new notification group."""
    require_permissions(["notification_group:create"])(current_user)
    logger.info(f"创建通知组 '{group_in.name}'", extra={"action": "notify.group_create", "group_name": group_in.name})

    group = await notification_group.create(db, obj_in=group_in)
    logger.info(f"通知组 '{group.name}' 创建成功，ID: {group.id}", extra={"action": "notify.group_create", "group_name": group.name, "group_id": group.id})

    return NotificationGroupResponse.model_validate(group)


@router.get("/{group_id}", response_model=NotificationGroupResponse)
async def get_notification_group(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get notification group by ID."""
    require_permissions(["notification_group:read"])(current_user)

    group = await notification_group.get_with_members(db, id=group_id)

    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="通知组不存在",
        )

    return NotificationGroupResponse.model_validate(group)


@router.put("/{group_id}", response_model=NotificationGroupResponse)
@audit_log(operation_type="UPDATE", module="notification_group", object_type="NotificationGroup")
async def update_notification_group(
    request: Request,
    group_id: int,
    group_in: NotificationGroupUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a notification group."""
    require_permissions(["notification_group:update"])(current_user)

    db_group = await notification_group.get_with_members(db, id=group_id)

    if not db_group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="通知组不存在",
        )

    updated_group = await notification_group.update(db, db_obj=db_group, obj_in=group_in)
    logger.info(f"通知组 '{updated_group.name}' 更新成功", extra={"action": "notify.group_update", "group_name": updated_group.name, "group_id": group_id})

    return NotificationGroupResponse.model_validate(updated_group)


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
@audit_log(operation_type="DELETE", module="notification_group", object_type="NotificationGroup")
async def delete_notification_group(
    request: Request,
    group_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a notification group."""
    require_permissions(["notification_group:delete"])(current_user)

    db_group = await notification_group.get(db, id=group_id)

    if not db_group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="通知组不存在",
        )

    await notification_group.delete(db, id=group_id)
    logger.info(f"通知组 ID={group_id} 删除成功", extra={"action": "notify.group_delete", "group_id": group_id})

    return None


@router.post("/{group_id}/members/{user_id}", response_model=NotificationGroupResponse)
@audit_log(operation_type="UPDATE", module="notification_group", object_type="NotificationGroup")
async def add_notification_group_member(
    request: Request,
    group_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a member to a notification group."""
    require_permissions(["notification_group:update"])(current_user)

    db_group = await notification_group.get_with_members(db, id=group_id)
    if not db_group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="通知组不存在",
        )

    db_user = await crud_user.get(db, id=user_id)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    updated_group = await notification_group.add_member(db, group_id=group_id, user_id=user_id)
    logger.info(f"向通知组 '{db_group.name}' 添加成员 user_id={user_id}", extra={"action": "notify.group_update", "group_name": db_group.name, "group_id": group_id, "user_id": user_id})

    return NotificationGroupResponse.model_validate(updated_group)


@router.delete("/{group_id}/members/{user_id}", response_model=NotificationGroupResponse)
@audit_log(operation_type="UPDATE", module="notification_group", object_type="NotificationGroup")
async def remove_notification_group_member(
    request: Request,
    group_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a member from a notification group."""
    require_permissions(["notification_group:update"])(current_user)

    db_group = await notification_group.get_with_members(db, id=group_id)
    if not db_group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="通知组不存在",
        )

    updated_group = await notification_group.remove_member(db, group_id=group_id, user_id=user_id)
    logger.info(f"从通知组 '{db_group.name}' 移除成员 user_id={user_id}", extra={"action": "notify.group_update", "group_name": db_group.name, "group_id": group_id, "user_id": user_id})

    return NotificationGroupResponse.model_validate(updated_group)
