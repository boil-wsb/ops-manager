"""
User management API routes.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db, require_permissions
from app.core.audit import audit_log
from app.core.cache import cache_delete_pattern, cache_get_or_set
from app.core.logging import get_logger
from app.crud.crud_user import crud_user
from app.crud.crud_user_ip_binding import crud_user_ip_binding
from app.models.permission import Role
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, UserUpdate

router = APIRouter(prefix="/users")
logger = get_logger(__name__)


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

    cache_key = f"users:list:{keyword}:{is_active}:{page}:{page_size}"

    async def _fetch_users():
        query = select(User).options(selectinload(User.roles)).options(selectinload(User.department))

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
                    "department_id": u.department_id,
                    "department_name": u.department.name if u.department else None,
                    "org_name": u.department.org_name if u.department else None,
                    "permissions": [],
                    "roles": [{"id": r.id, "name": r.name} for r in u.roles],
                }
                for u in users
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    return await cache_get_or_set(cache_key, _fetch_users, ttl=30)


@router.get("/ip-bindings")
async def list_ip_bindings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["user:read"])),
):
    """获取所有用户 IP 绑定列表（管理员）。"""
    bindings = await crud_user_ip_binding.get_all(db, skip=0, limit=500)

    # Enrich with user info
    result = []
    for b in bindings:
        user = await crud_user.get(db, id=b.user_id)
        result.append({
            "id": b.id,
            "user_id": b.user_id,
            "username": user.username if user else None,
            "full_name": user.full_name if user else None,
            "ip_address": b.ip_address,
            "bound_at": b.bound_at,
        })

    return {"items": result, "total": len(result)}


@router.post("", status_code=status.HTTP_201_CREATED)
@audit_log(operation_type="CREATE", module="user", object_type="User")
async def create_user(
    request: Request,
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["user:create"])),
):
    """创建新用户"""
    logger.info(
        f"创建用户 '{user_in.username}'",
        extra={"action": "user.create", "username": user_in.username},
    )

    existing_user = await crud_user.get_by_username(db, username=user_in.username)
    if existing_user:
        logger.warning(
            f"用户名 '{user_in.username}' 已存在",
            extra={"action": "user.create", "username": user_in.username},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在",
        )

    if user_in.email:
        existing_email = await crud_user.get_by_email(db, email=user_in.email)
        if existing_email:
            logger.warning(
                f"邮箱 '{user_in.email}' 已存在",
                extra={"action": "user.create", "email": user_in.email},
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邮箱已存在",
            )

    user = await crud_user.create(db, obj_in=user_in)
    logger.info(
        f"用户 '{user_in.username}' 创建成功，ID: {user.id}",
        extra={"action": "user.create", "username": user_in.username, "user_id": user.id},
    )

    await cache_delete_pattern("users:list:*")

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
    logger.info(f"更新用户 ID={user_id}", extra={"action": "user.update", "user_id": user_id})

    user = await crud_user.get(db, id=user_id)
    if not user:
        logger.warning(
            f"用户 ID={user_id} 不存在", extra={"action": "user.update", "user_id": user_id}
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    if user_in.email and user_in.email != user.email:
        existing_email = await crud_user.get_by_email(db, email=user_in.email)
        if existing_email:
            logger.warning(
                f"邮箱 '{user_in.email}' 已被其他用户使用",
                extra={"action": "user.update", "email": user_in.email},
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邮箱已存在",
            )

    if user_in.is_superuser is not None and not current_user.is_superuser:
        logger.warning("非超级管理员无权修改超级管理员权限", extra={"action": "user.update"})
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有超级管理员才能修改超级管理员权限",
        )

    user = await crud_user.update(db, db_obj=user, obj_in=user_in)
    logger.info(
        f"用户 '{user.username}' 更新成功",
        extra={"action": "user.update", "username": user.username, "user_id": user.id},
    )

    await cache_delete_pattern("users:list:*")

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
    logger.info(f"删除用户 ID={user_id}", extra={"action": "user.delete", "user_id": user_id})

    user = await crud_user.get(db, id=user_id)
    if not user:
        logger.warning(
            f"用户 ID={user_id} 不存在", extra={"action": "user.delete", "user_id": user_id}
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    username = user.username
    await crud_user.delete(db, id=user_id)
    logger.info(
        f"用户 '{username}' 删除成功",
        extra={"action": "user.delete", "username": username, "user_id": user_id},
    )

    await cache_delete_pattern("users:list:*")

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

    roles_result = await db.execute(select(Role).where(Role.id.in_(role_ids)))
    roles = list(roles_result.scalars().all())
    found_ids = {r.id for r in roles}
    missing_ids = set(role_ids) - found_ids
    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"角色ID {', '.join(str(i) for i in missing_ids)} 不存在",
        )

    old_role_ids = [r.id for r in user.roles]

    user.roles = roles
    await db.commit()

    await cache_delete_pattern("users:list:*")

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

    await cache_delete_pattern("users:list:*")

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
    existing_result = await db.execute(select(User.id).where(User.id.in_(user_ids)))
    existing_ids = set(existing_result.scalars().all())
    missing_ids = set(user_ids) - existing_ids

    if existing_ids:
        await db.execute(delete(User).where(User.id.in_(existing_ids)))
        await db.commit()

    await cache_delete_pattern("users:list:*")

    return {
        "deleted_count": len(existing_ids),
        "failed_count": len(missing_ids),
        "deleted_ids": list(existing_ids),
        "failed_ids": list(missing_ids),
    }


class SendMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000, description="消息内容")


@router.post("/{user_id}/send-message")
@audit_log(operation_type="SEND_MESSAGE", module="user", object_type="User")
async def send_message_to_user(
    request: Request,
    user_id: int,
    msg_in: SendMessageRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["user:write"])),
):
    """通过飞书发送消息给指定用户"""
    user = await crud_user.get(db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    if not user.feishu_open_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"用户 {user.username} 未绑定飞书账号，无法发送消息",
        )

    try:
        from app.integrations.feishu.service import get_feishu_service

        feishu_service = get_feishu_service()
        result = feishu_service.send_text_message(
            user_id=user.feishu_open_id,
            text=msg_in.message,
        )

        if result.get("message_id"):
            logger.info(
                f"消息发送成功: user={user.username}",
                extra={"action": "user.send_message", "username": user.username},
            )
            return {"success": True, "message_id": result["message_id"]}
        else:
            error_msg = result.get("msg", "Unknown error")
            logger.error(
                f"消息发送失败: user={user.username}, error={error_msg}",
                extra={"action": "user.send_message", "username": user.username, "error": error_msg},
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"消息发送失败: {error_msg}",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"消息发送异常: user={user.username}, error={str(e)}",
            extra={"action": "user.send_message", "username": user.username, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"消息发送失败: {str(e)}",
        ) from e


@router.delete("/{user_id}/ip-binding", status_code=status.HTTP_200_OK)
@audit_log(operation_type="DELETE", module="user", object_type="UserIpBinding")
async def unbind_user_ip(
    request: Request,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["user:write"])),
):
    """解绑指定用户的 IP 绑定（管理员）。"""
    user = await crud_user.get(db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    deleted = await crud_user_ip_binding.delete_binding(db, user_id=user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="该用户没有 IP 绑定记录",
        )

    logger.info(
        f"管理员解绑用户 {user.username}(id={user_id}) 的 IP 绑定",
        extra={"action": "user.unbind_ip", "user_id": user_id, "operator": current_user.username},
    )

    return {"message": "IP 绑定已解绑", "user_id": user_id}
