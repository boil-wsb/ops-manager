"""
API dependencies.
"""

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.core.security import verify_token
from app.crud.crud_user import crud_user
from app.db.session import get_db

security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get current user from JWT token."""
    if not credentials:
        raise AuthenticationError(detail="Not authenticated")

    token = credentials.credentials
    payload = verify_token(token)

    if payload is None:
        raise AuthenticationError(detail="Invalid or expired token")

    if payload.get("type") != "access":
        raise AuthenticationError(detail="Invalid token type")

    user_id = payload.get("sub")
    if user_id is None:
        raise AuthenticationError(detail="Invalid token payload")

    user = await crud_user.get(db, id=int(user_id))

    if not user:
        raise AuthenticationError(detail="User not found")

    if not user.is_active:
        raise AuthenticationError(detail="User is inactive")

    request.state.user = user

    return user


async def get_current_user_optional(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> dict | None:
    """Get current user from JWT token, returns None if not authenticated."""
    if not credentials:
        return None

    token = credentials.credentials
    payload = verify_token(token)

    if payload is None:
        return None

    if payload.get("type") != "access":
        return None

    user_id = payload.get("sub")
    if user_id is None:
        return None

    user = await crud_user.get(db, id=int(user_id))

    if not user or not user.is_active:
        return None

    request.state.user = user

    return user


async def get_current_active_user(
    current_user=Depends(get_current_user),
) -> dict:
    """Get current active user."""
    return current_user


class PermissionChecker:
    """Permission checker dependency."""

    def __init__(self, required_permissions: list[str]):
        self.required_permissions = required_permissions

    async def __call__(
        self,
        current_user=Depends(get_current_user),
    ) -> dict:
        """Check if user has required permissions."""
        user_permissions = []
        for role in current_user.roles:
            user_permissions.extend(role.permissions or [])

        has_permission = any(
            perm in user_permissions for perm in self.required_permissions
        )

        if current_user.is_superuser:
            has_permission = True

        if not has_permission:
            raise PermissionDeniedError(
                detail=f"Missing required permissions: {self.required_permissions}"
            )

        return current_user


def require_permissions(permissions: list[str]):
    """Create a permission checker dependency.

    Usage:
        @router.get("/items")
        async def list_items(
            current_user: User = Depends(require_permissions(["item:read"]))
        ):
            ...
    """
    return PermissionChecker(permissions)
