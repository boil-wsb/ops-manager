"""
User management API routes.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/users")


@router.get("")
async def list_users():
    """List all users."""
    pass


@router.post("")
async def create_user():
    """Create a new user."""
    pass


@router.get("/{user_id}")
async def get_user(user_id: int):
    """Get user by ID."""
    pass


@router.put("/{user_id}")
async def update_user(user_id: int):
    """Update user."""
    pass


@router.delete("/{user_id}")
async def delete_user(user_id: int):
    """Delete user."""
    pass
