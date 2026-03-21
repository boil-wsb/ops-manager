"""
Permission checking utilities.
"""

from fastapi import HTTPException, status
from fastapi.security import HTTPBearer

from app.models.user import User

security = HTTPBearer(auto_error=False)


def get_user_permissions(user: User) -> list[str]:
    """Get all permission codes for a user."""
    # Superuser has all permissions
    if user.is_superuser:
        return ["*"]

    permissions = set()
    for role in user.roles:
        if role.is_active:
            for perm in role.permissions:
                if perm.is_active:
                    permissions.add(perm.code)

    return list(permissions)


def has_permission(user: User, permission_code: str) -> bool:
    """Check if user has specific permission."""
    # Superuser has all permissions
    if user.is_superuser:
        return True

    # Get all user permissions
    user_permissions = get_user_permissions(user)

    # Check for wildcard permission
    if "*" in user_permissions:
        return True

    # Check for specific permission
    return permission_code in user_permissions


def has_any_permission(user: User, permission_codes: list[str]) -> bool:
    """Check if user has any of the specified permissions."""
    return any(has_permission(user, code) for code in permission_codes)


def has_all_permissions(user: User, permission_codes: list[str]) -> bool:
    """Check if user has all of the specified permissions."""
    return all(has_permission(user, code) for code in permission_codes)


class PermissionChecker:
    """Permission checker class."""

    def __init__(self, required_permissions: list[str], require_all: bool = False):
        self.required_permissions = required_permissions
        self.require_all = require_all

    def __call__(self, current_user: User):
        """Check if user has required permissions."""
        # Superuser bypass
        if current_user.is_superuser:
            return None

        # Check permissions
        if self.require_all:
            has_perm = has_all_permissions(current_user, self.required_permissions)
        else:
            has_perm = has_any_permission(current_user, self.required_permissions)

        if not has_perm:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"缺少所需权限: {', '.join(self.required_permissions)}",
            )

        return None


# Create global checker instances
require_role_read = PermissionChecker(["role:read"])
require_role_create = PermissionChecker(["role:create"])
require_role_update = PermissionChecker(["role:update"])
require_role_delete = PermissionChecker(["role:delete"])


def require_permissions(permissions: list[str], require_all: bool = False):
    """Create a permission checker dependency.

    Usage:
        @router.get("/items")
        async def list_items(
            current_user: User = Depends(get_current_user),
            _: None = Depends(require_permissions(["item:read"]))
        ):
            ...
    """
    checker = PermissionChecker(permissions, require_all)
    return checker


def check_permission(user: User, permission_code: str):
    """Check permission and raise exception if not authorized.

    Usage:
        check_permission(current_user, "item:delete")
    """
    if not has_permission(user, permission_code):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"缺少所需权限: {permission_code}",
        )
