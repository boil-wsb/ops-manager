"""
User management API routes.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_permissions
from app.core.audit import audit_log
from app.crud.crud_role import crud_role
from app.crud.crud_user import crud_user
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, UserUpdate

router = APIRouter(prefix="/users")
logger = logging.getLogger(__name__)


@router.get("")
async def list_users(
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    is_active: bool | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["user:read"])),
):
    """Get user list with filters."""
    skip = (page - 1) * page_size

    query = select(User)

    if keyword:
        query = query.where(
            (User.username.ilike(f"%{keyword}%"))
            | (User.email.ilike(f"%{keyword}%"))
            | (User.full_name.ilike(f"%{keyword}%"))
        )

    if is_active is not None:
        query = query.where(User.is_active == is_active)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    query = query.offset(skip).limit(page_size)
    result = await db.execute(query)
    users = result.scalars().all()

    return {
        "items": [
            {
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "full_name": u.full_name,
                "is_active": u.is_active,
                "is_superuser": u.is_superuser,
                "last_login": u.last_login,
                "created_at": u.created_at,
                "updated_at": u.updated_at,
                "feishu_open_id": u.feishu_open_id,
                "permissions": [],
                "roles": [],
            }
            for u in users
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
@audit_log(operation_type="CREATE", module="user", object_type="User")
async def create_user(
    request: Request,
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["user:create"])),
):
    """创建新用户"""
    logger.info(f"[用户管理] 创建用户 '{user_in.username}'")

    existing_user = await crud_user.get_by_username(db, username=user_in.username)
    if existing_user:
        logger.warning(f"[用户管理] 用户名 '{user_in.username}' 已存在")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在",
        )

    if user_in.email:
        existing_email = await crud_user.get_by_email(db, email=user_in.email)
        if existing_email:
            logger.warning(f"[用户管理] 邮箱 '{user_in.email}' 已存在")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邮箱已存在",
            )

    user = await crud_user.create(db, obj_in=user_in)
    logger.info(f"[用户管理] 用户 '{user_in.username}' 创建成功，ID: {user.id}")

    return UserResponse.model_validate(user)


@router.get("/{user_id}")
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["user:read"])),
):
    """Get user by ID."""
    user = await crud_user.get(db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )
    return UserResponse.model_validate(user)


@router.put("/{user_id}")
@audit_log(operation_type="UPDATE", module="user", object_type="User")
async def update_user(
    request: Request,
    user_id: int,
    user_in: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["user:update"])),
):
    """更新用户"""
    logger.info(f"[用户管理] 更新用户 ID={user_id}")

    user = await crud_user.get(db, id=user_id)
    if not user:
        logger.warning(f"[用户管理] 用户 ID={user_id} 不存在")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    if user_in.email and user_in.email != user.email:
        existing_email = await crud_user.get_by_email(db, email=user_in.email)
        if existing_email:
            logger.warning(f"[用户管理] 邮箱 '{user_in.email}' 已被其他用户使用")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邮箱已存在",
            )

    if user_in.is_superuser is not None and not current_user.is_superuser:
        logger.warning("[用户管理] 非超级管理员无权修改超级管理员权限")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有超级管理员才能修改超级管理员权限",
        )

    user = await crud_user.update(db, db_obj=user, obj_in=user_in)
    logger.info(f"[用户管理] 用户 '{user.username}' 更新成功")

    return UserResponse.model_validate(user)


@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
@audit_log(operation_type="DELETE", module="user", object_type="User")
async def delete_user(
    request: Request,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["user:delete"])),
):
    """删除用户"""
    logger.info(f"[用户管理] 删除用户 ID={user_id}")

    user = await crud_user.get(db, id=user_id)
    if not user:
        logger.warning(f"[用户管理] 用户 ID={user_id} 不存在")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    username = user.username
    await crud_user.delete(db, id=user_id)
    logger.info(f"[用户管理] 用户 '{username}' 删除成功")

    return {"success": True}


@router.post("/{user_id}/roles")
@audit_log(operation_type="ASSIGN_ROLE", module="user", object_type="User")
async def assign_user_roles(
    request: Request,
    user_id: int,
    role_ids: list[int],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["user:update"])),
):
    """Assign roles to user."""
    user = await crud_user.get(db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    roles = []
    for role_id in role_ids:
        role = await crud_role.get(db, id=role_id)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"角色ID {role_id} 不存在",
            )
        roles.append(role)

    old_role_ids = [r.id for r in user.roles]

    user.roles = roles
    await db.commit()

    return {
        "user_id": user.id,
        "roles": [{"id": r.id, "name": r.name} for r in roles],
        "old_roles": old_role_ids,
    }


@router.delete("/{user_id}/roles", status_code=status.HTTP_200_OK)
@audit_log(operation_type="REVOKE_ROLE", module="user", object_type="User")
async def revoke_user_roles(
    request: Request,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["user:update"])),
):
    """Revoke all roles from user."""
    user = await crud_user.get(db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    user.roles = []
    await db.commit()

    return {"success": True}


@router.post("/batch-delete", status_code=status.HTTP_200_OK)
@audit_log(operation_type="BATCH_DELETE", module="user", object_type="User")
async def batch_delete_users(
    request: Request,
    user_ids: list[int],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["user:delete"])),
):
    """Batch delete users."""
    deleted_ids = []
    failed_ids = []

    for user_id in user_ids:
        user = await crud_user.get(db, id=user_id)
        if user:
            await crud_user.delete(db, id=user_id)
            deleted_ids.append(user_id)
        else:
            failed_ids.append(user_id)

    return {
        "deleted_count": len(deleted_ids),
        "failed_count": len(failed_ids),
        "deleted_ids": deleted_ids,
        "failed_ids": failed_ids,
    }