"""
User CRUD operations.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.crud.base import CRUDBase
from app.models.permission import Role
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    """User CRUD operations."""

    async def get_by_username(
        self,
        db: AsyncSession,
        *,
        username: str
    ) -> User | None:
        """Get user by username."""
        result = await db.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def get_by_email(
        self,
        db: AsyncSession,
        *,
        email: str
    ) -> User | None:
        """Get user by email."""
        result = await db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        db: AsyncSession,
        *,
        obj_in: UserCreate
    ) -> User:
        """Create a new user with hashed password."""
        db_obj = User(
            username=obj_in.username,
            email=obj_in.email,
            full_name=obj_in.full_name,
            hashed_password=get_password_hash(obj_in.password),
            is_active=obj_in.is_active,
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)

        # Assign roles if provided
        if obj_in.role_ids:
            for role_id in obj_in.role_ids:
                role_result = await db.execute(
                    select(Role).where(Role.id == role_id)
                )
                role = role_result.scalar_one_or_none()
                if role:
                    db_obj.roles.append(role)
            await db.commit()
            await db.refresh(db_obj)

        return db_obj

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: User,
        obj_in: UserUpdate
    ) -> User:
        """Update user."""
        update_data = obj_in.model_dump(exclude_unset=True)

        # Handle password update
        if "password" in update_data and update_data["password"]:
            update_data["hashed_password"] = get_password_hash(update_data.pop("password"))

        # Handle role_ids separately
        role_ids = update_data.pop("role_ids", None)

        # Update other fields
        for field, value in update_data.items():
            setattr(db_obj, field, value)

        # Update roles if provided
        if role_ids is not None:
            db_obj.roles = []
            for role_id in role_ids:
                role_result = await db.execute(
                    select(Role).where(Role.id == role_id)
                )
                role = role_result.scalar_one_or_none()
                if role:
                    db_obj.roles.append(role)

        await db.commit()
        await db.refresh(db_obj)
        return db_obj


crud_user = CRUDUser(User)
