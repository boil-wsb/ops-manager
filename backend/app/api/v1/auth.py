"""
Authentication API routes.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.user import UserLogin, UserResponse, TokenResponse

router = APIRouter(prefix="/auth")


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """User login."""
    # TODO: Implement login logic
    pass


@router.post("/logout")
async def logout():
    """User logout."""
    # TODO: Implement logout logic
    pass


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token():
    """Refresh access token."""
    # TODO: Implement token refresh
    pass


@router.get("/me", response_model=UserResponse)
async def get_current_user_info():
    """Get current user info."""
    # TODO: Implement get current user
    pass
