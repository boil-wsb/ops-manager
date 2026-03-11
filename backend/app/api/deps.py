"""
API dependencies.
"""
from typing import Optional, List
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.security import verify_token
from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.crud.crud_user import crud_user

# Security scheme
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Get current user from JWT token."""
    if not credentials:
        raise AuthenticationError(detail="Not authenticated")
    
    token = credentials.credentials
    user_id = verify_token(token, token_type="access")
    
    if user_id is None:
        raise AuthenticationError(detail="Invalid or expired token")
    
    user = await crud_user.get(db, id=int(user_id))
    
    if not user:
        raise AuthenticationError(detail="User not found")
    
    if not user.is_active:
        raise AuthenticationError(detail="User is inactive")
    
    return user


async def get_current_active_user(
    current_user = Depends(get_current_user)
) -> dict:
    """Get current active user."""
    return current_user


class PermissionChecker:
    """Permission checker dependency."""
    
    def __init__(self, required_permissions: List[str]):
        self.required_permissions = required_permissions
    
    async def __call__(
        self,
        current_user = Depends(get_current_user)
    ) -> dict:
        """Check if user has required permissions."""
        # Get user permissions from roles
        user_permissions = []
        for role in current_user.roles:
            user_permissions.extend(role.permissions or [])
        
        # Check if user has any of the required permissions
        has_permission = any(
            perm in user_permissions 
            for perm in self.required_permissions
        )
        
        # Superuser has all permissions
        if current_user.is_superuser:
            has_permission = True
        
        if not has_permission:
            raise PermissionDeniedError(
                detail=f"Missing required permissions: {self.required_permissions}"
            )
        
        return current_user


def require_permissions(permissions: List[str]):
    """Decorator to require specific permissions."""
    return Depends(PermissionChecker(permissions))
