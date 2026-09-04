"""Authentication API routes."""

import hashlib

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.config import settings
from app.core.audit import audit_log
from app.core.logging import get_logger
from app.core.rate_limit import limiter
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_client_ip,
    get_password_hash,
    verify_password,
    verify_token,
)
from app.core.tz import now_shanghai
from app.crud.crud_user import crud_user
from app.crud.crud_user_ip_binding import crud_user_ip_binding
from app.models.user import User
from app.schemas.user import (
    ChangePassword,
    EmployeeLoginRequest,
    TokenResponse,
    UserLogin,
    UserResponse,
)

router = APIRouter(prefix="/auth")
security = HTTPBearer(auto_error=False)
logger = get_logger(__name__)


def extract_user_permissions(user: User) -> list[str]:
    """Extract all permissions from user's roles."""
    if user.is_superuser:
        return ["*"]

    permissions: set[str] = set()
    for role in user.roles:
        if role.is_active:
            for permission in role.permissions:
                if permission.is_active:
                    permissions.add(permission.code)

    return sorted(permissions)


def compute_permission_version(permissions: list[str]) -> str | None:
    """计算权限版本号：对排序后的权限代码做 sha1 哈希。

    权限发生变化（增/删/改角色分配）时版本号必然变化，
    前端据此判断本地缓存是否需要刷新。
    """
    if not permissions:
        return None
    raw = "|".join(permissions).encode("utf-8")
    return hashlib.sha1(raw).hexdigest()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get current user from JWT token."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证凭据",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = verify_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的访问令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的令牌类型",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的令牌内容",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await crud_user.get(db, id=int(user_id))

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户已被禁用",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
@audit_log(operation_type="LOGIN", module="system")
async def login(
    request: Request,
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    """用户登录"""
    logger.info(
        f"用户 '{credentials.username}' 尝试登录",
        extra={"action": "user.login", "username": credentials.username},
    )

    user = await crud_user.get_by_username(db, username=credentials.username)

    if not user:
        logger.warning(
            f"用户 '{credentials.username}' 不存在",
            extra={"action": "user.login", "username": credentials.username},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        logger.warning(
            f"用户 '{credentials.username}' 已被禁用",
            extra={"action": "user.login", "username": credentials.username},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户已被禁用",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(credentials.password, user.hashed_password):
        logger.warning(
            f"用户 '{credentials.username}' 密码错误",
            extra={"action": "user.login", "username": credentials.username},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # IP binding check: only for Feishu-synced non-superuser users
    if user.is_feishu_user and not user.is_superuser:
        client_ip = get_client_ip(request)
        if client_ip:
            existing_binding = await crud_user_ip_binding.get_by_user_id(db, user_id=user.id)
            if existing_binding:
                if existing_binding.ip_address != client_ip:
                    logger.warning(
                        f"用户 '{credentials.username}' IP不匹配: "
                        f"绑定IP={existing_binding.ip_address}, 当前IP={client_ip}",
                        extra={
                            "action": "user.login",
                            "username": credentials.username,
                            "bound_ip": existing_binding.ip_address,
                            "current_ip": client_ip,
                        },
                    )
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"该账号已绑定IP {existing_binding.ip_address}，"
                        f"无法从当前IP({client_ip})登录",
                    )
            else:
                # User not bound yet, check if IP is already taken
                ip_binding = await crud_user_ip_binding.get_by_ip(db, ip_address=client_ip)
                if ip_binding:
                    logger.warning(
                        f"IP {client_ip} 已绑定其他用户(id={ip_binding.user_id})",
                        extra={
                            "action": "user.login",
                            "username": credentials.username,
                            "ip": client_ip,
                            "bound_user_id": ip_binding.user_id,
                        },
                    )
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="该IP已绑定其他账号，无法登录",
                    )
                # Create binding
                await crud_user_ip_binding.create_binding(db, user_id=user.id, ip_address=client_ip)
                logger.info(
                    f"用户 '{credentials.username}' 首次登录，绑定IP: {client_ip}",
                    extra={
                        "action": "user.login",
                        "username": credentials.username,
                        "ip": client_ip,
                    },
                )

    user.last_login = now_shanghai()
    await db.commit()
    await db.refresh(user)

    # 待改密标记：由用户表 must_change_password 决定（改密成功后清除并重签 token）
    pwd_change_required = user.must_change_password
    token_payload = {"sub": str(user.id), "pwd_change_required": pwd_change_required}
    access_token = create_access_token(data=dict(token_payload))
    refresh_token = create_refresh_token(data=dict(token_payload))

    permissions = extract_user_permissions(user)

    logger.info(
        f"用户 '{credentials.username}' 登录成功，权限数量: {len(permissions)}",
        extra={
            "action": "user.login",
            "username": credentials.username,
            "permissions_count": len(permissions),
            "must_change_password": pwd_change_required,
        },
    )

    user_roles = [{"id": role.id, "name": role.name} for role in user.roles if role.is_active]

    permission_version = compute_permission_version(permissions)

    user_response = UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        last_login=user.last_login,
        created_at=user.created_at,
        updated_at=user.updated_at,
        permissions=permissions,
        roles=user_roles,
        permission_version=permission_version,
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
        permissions=permissions,
        permission_version=permission_version,
        must_change_password=pwd_change_required,
        user=user_response,
    )


@router.post("/external/login", response_model=TokenResponse)
@limiter.limit("60/minute")
@audit_log(operation_type="LOGIN", module="system")
async def employee_login(
    request: Request,
    credentials: EmployeeLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """工号登录（外部服务）。

    外部服务携带工号+密码登录本服务，首次登录（must_change_password=true）时
    签发携带待改密标记的 token，业务接口将被拦截，直到调用 /auth/change-password
    完成改密并重新签发正常 token。
    """
    logger.info(
        f"工号 '{credentials.employee_id}' 尝试登录",
        extra={"action": "user.employee_login", "employee_id": credentials.employee_id},
    )

    user = await crud_user.get_by_employee_id(db, employee_id=credentials.employee_id)

    if not user:
        logger.warning(
            f"工号 '{credentials.employee_id}' 不存在",
            extra={"action": "user.employee_login", "employee_id": credentials.employee_id},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="工号或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        logger.warning(
            f"工号 '{credentials.employee_id}' 已被禁用",
            extra={"action": "user.employee_login", "employee_id": credentials.employee_id},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(credentials.password, user.hashed_password):
        logger.warning(
            f"工号 '{credentials.employee_id}' 密码错误",
            extra={"action": "user.employee_login", "employee_id": credentials.employee_id},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="工号或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user.last_login = now_shanghai()
    await db.commit()
    await db.refresh(user)

    # 待改密标记：由用户表 must_change_password 决定，改密成功后清除并重签 token
    pwd_change_required = user.must_change_password
    token_payload = {"sub": str(user.id), "pwd_change_required": pwd_change_required}
    access_token = create_access_token(data=dict(token_payload))
    refresh_token = create_refresh_token(data=dict(token_payload))

    permissions = extract_user_permissions(user)
    permission_version = compute_permission_version(permissions)

    logger.info(
        f"工号 '{credentials.employee_id}' 登录成功，待改密: {pwd_change_required}",
        extra={
            "action": "user.employee_login",
            "employee_id": credentials.employee_id,
            "must_change_password": pwd_change_required,
            "permissions_count": len(permissions),
        },
    )

    user_roles = [{"id": role.id, "name": role.name} for role in user.roles if role.is_active]

    user_response = UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        last_login=user.last_login,
        created_at=user.created_at,
        updated_at=user.updated_at,
        permissions=permissions,
        roles=user_roles,
        permission_version=permission_version,
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
        permissions=permissions,
        permission_version=permission_version,
        must_change_password=pwd_change_required,
        user=user_response,
    )


@router.post("/logout")
@audit_log(operation_type="LOGOUT", module="system")
async def logout(request: Request):
    """User logout."""
    return {"message": "退出登录成功"}


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_token: str,
    db: AsyncSession = Depends(get_db),
):
    """Refresh access token."""
    payload = verify_token(refresh_token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的刷新令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的令牌类型",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的令牌内容",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 实时读取用户待改密状态，保证刷新后的 token 标记一致（改密前刷新不绕过强制改密）
    pwd_change_required = False
    permissions: list[str] = []
    user = await crud_user.get(db, id=int(user_id))
    if user is not None and user.is_active:
        pwd_change_required = user.must_change_password
        permissions = extract_user_permissions(user)

    token_payload = {"sub": user_id, "pwd_change_required": pwd_change_required}
    new_access_token = create_access_token(data=dict(token_payload))
    new_refresh_token = create_refresh_token(data=dict(token_payload))

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
        permissions=permissions,
        permission_version=compute_permission_version(permissions),
        must_change_password=pwd_change_required,
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """Get current user info."""
    permissions = extract_user_permissions(current_user)
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        is_superuser=current_user.is_superuser,
        last_login=current_user.last_login,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
        permissions=permissions,
        permission_version=compute_permission_version(permissions),
    )


@router.post("/change-password")
@audit_log(operation_type="CHANGE_PASSWORD", module="system")
async def change_password(
    request: Request,
    data: ChangePassword,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """修改密码"""
    logger.info(
        f"用户 '{current_user.username}' 尝试修改密码",
        extra={"action": "user.change_password", "username": current_user.username},
    )

    if not verify_password(data.old_password, current_user.hashed_password):
        logger.warning(
            f"用户 '{current_user.username}' 当前密码错误",
            extra={"action": "user.change_password", "username": current_user.username},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="当前密码错误",
        )

    current_user.hashed_password = get_password_hash(data.new_password)
    # 改密成功后清除待改密标记（首次登录强制改密场景）
    was_pending = current_user.must_change_password
    current_user.must_change_password = False
    await db.commit()

    # 重新签发无待改密标记的 token，调用方可直接替换本地令牌
    token_payload = {"sub": str(current_user.id), "pwd_change_required": False}
    access_token = create_access_token(data=dict(token_payload))
    refresh_token = create_refresh_token(data=dict(token_payload))

    logger.info(
        f"用户 '{current_user.username}' 密码修改成功，待改密标记清除: {was_pending}",
        extra={
            "action": "user.change_password",
            "username": current_user.username,
            "must_change_password_cleared": was_pending,
        },
    )

    return {
        "message": "密码修改成功",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60,
        "must_change_password": False,
    }
