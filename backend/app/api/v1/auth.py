"""
Authentication API routes.
"""

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
from app.schemas.user import ChangePassword, TokenResponse, UserLogin, UserResponse

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
            existing_binding = await crud_user_ip_binding.get_by_user_id(
                db, user_id=user.id
            )
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
                ip_binding = await crud_user_ip_binding.get_by_ip(
                    db, ip_address=client_ip
                )
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
                await crud_user_ip_binding.create_binding(
                    db, user_id=user.id, ip_address=client_ip
                )
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

    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    permissions = extract_user_permissions(user)

    logger.info(
        f"用户 '{credentials.username}' 登录成功，权限数量: {len(permissions)}",
        extra={
            "action": "user.login",
            "username": credentials.username,
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
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
        permissions=permissions,
        user=user_response,
    )


@router.post("/logout")
@audit_log(operation_type="LOGOUT", module="system")
async def logout(request: Request):
    """User logout."""
    return {"message": "退出登录成功"}


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(refresh_token: str):
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

    new_access_token = create_access_token(data={"sub": user_id})
    new_refresh_token = create_refresh_token(data={"sub": user_id})

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
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
    await db.commit()

    logger.info(
        f"用户 '{current_user.username}' 密码修改成功",
        extra={"action": "user.change_password", "username": current_user.username},
    )

    return {"message": "密码修改成功"}
