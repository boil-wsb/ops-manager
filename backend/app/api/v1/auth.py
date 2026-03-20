"""
Authentication API routes.
"""
from datetime import datetime
from typing import Optional, List, Set
import logging

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.crud.crud_user import crud_user
from app.schemas.user import UserLogin, UserResponse, TokenResponse, ChangePassword
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    verify_token,
)
from app.core.audit import audit_log
from app.config import settings
from app.models.user import User
from app.core.rate_limit import limiter

router = APIRouter(prefix="/auth")
security = HTTPBearer(auto_error=False)
logger = logging.getLogger(__name__)


def extract_user_permissions(user: User) -> List[str]:
    """Extract all permissions from user's roles."""
    if user.is_superuser:
        return ["*"]
    
    permissions: Set[str] = set()
    for role in user.roles:
        if role.is_active:
            for permission in role.permissions:
                if permission.is_active:
                    permissions.add(permission.code)
    
    return sorted(list(permissions))


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
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
    db: AsyncSession = Depends(get_db)
):
    """用户登录"""
    logger.info(f"[登录] 用户 '{credentials.username}' 尝试登录")
    
    user = await crud_user.get_by_username(db, username=credentials.username)
    
    if not user:
        logger.warning(f"[登录] 用户 '{credentials.username}' 不存在")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        logger.warning(f"[登录] 用户 '{credentials.username}' 已被禁用")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户已被禁用",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not verify_password(credentials.password, user.hashed_password):
        logger.warning(f"[登录] 用户 '{credentials.username}' 密码错误")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user.last_login = datetime.utcnow()
    await db.commit()
    await db.refresh(user)
    
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    permissions = extract_user_permissions(user)
    
    logger.info(f"[登录] 用户 '{credentials.username}' 登录成功，权限数量: {len(permissions)}")
    
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
    # In a more complex implementation, you might want to blacklist the token
    # For now, we just return success and let the client delete the token
    return {"message": "退出登录成功"}


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(refresh_token: str):
    """Refresh access token."""
    # Verify refresh token
    payload = verify_token(refresh_token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的刷新令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check token type
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的令牌类型",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user_id from subject
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的令牌内容",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create new tokens
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
    current_user: User = Depends(get_current_user)
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
    logger.info(f"[密码修改] 用户 '{current_user.username}' 尝试修改密码")
    
    if not verify_password(data.old_password, current_user.hashed_password):
        logger.warning(f"[密码修改] 用户 '{current_user.username}' 当前密码错误")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="当前密码错误",
        )
    
    current_user.hashed_password = get_password_hash(data.new_password)
    await db.commit()
    
    logger.info(f"[密码修改] 用户 '{current_user.username}' 密码修改成功")
    
    return {"message": "密码修改成功"}
