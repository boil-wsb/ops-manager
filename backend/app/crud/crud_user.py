"""
User CRUD operations.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload, selectinload

from app.core.security import get_password_hash
from app.core.tz import now_shanghai
from app.crud.base import CRUDBase
from app.models.permission import Role
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    """User CRUD operations."""

    async def get(self, db: AsyncSession, id: int) -> User | None:
        """Get a user by ID with roles preloaded."""
        result = await db.execute(
            select(User).options(selectinload(User.roles)).where(User.id == id)
        )
        return result.scalar_one_or_none()

    async def get_for_auth(self, db: AsyncSession, id: int) -> User | None:
        """Get a user by ID for authentication check only.

        Loads roles (needed for permission checks in downstream requests)
        but skips loading department to reduce query overhead.
        """
        result = await db.execute(
            select(User)
            .options(selectinload(User.roles), noload(User.department))
            .where(User.id == id)
        )
        return result.scalar_one_or_none()

    async def get_by_username(self, db: AsyncSession, *, username: str) -> User | None:
        """Get user by username."""
        result = await db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def get_by_email(self, db: AsyncSession, *, email: str) -> User | None:
        """Get user by email."""
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_full_name(self, db: AsyncSession, *, full_name: str) -> User | None:
        """Get user by full_name."""
        result = await db.execute(select(User).where(User.full_name == full_name))
        return result.scalar_one_or_none()

    async def get_by_feishu_open_id(self, db: AsyncSession, *, feishu_open_id: str) -> User | None:
        """Get user by Feishu open_id."""
        result = await db.execute(select(User).where(User.feishu_open_id == feishu_open_id))
        return result.scalar_one_or_none()

    async def get_all_feishu_users(
        self,
        db: AsyncSession,
    ) -> list[User]:
        """Get all Feishu-synced users."""
        result = await db.execute(select(User).where(User.is_feishu_user))
        return list(result.scalars().all())

    async def _get_roles_by_ids(self, db: AsyncSession, role_ids: list[int]) -> list[Role]:
        """Batch fetch roles by IDs."""
        if not role_ids:
            return []
        result = await db.execute(select(Role).where(Role.id.in_(role_ids)))
        return list(result.scalars().all())

    async def create(self, db: AsyncSession, *, obj_in: UserCreate) -> User:
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

        if obj_in.role_ids:
            roles = await self._get_roles_by_ids(db, obj_in.role_ids)
            db_obj.roles = roles
            await db.commit()
            await db.refresh(db_obj)

        return db_obj

    async def create_feishu_user(
        self,
        db: AsyncSession,
        *,
        feishu_open_id: str,
        feishu_union_id: str | None,
        username: str,
        full_name: str | None,
        email: str | None,
        mobile: str | None,
        hashed_password: str,
        role_ids: list[int] | None = None,
        employee_no: str | None = None,
    ) -> User:
        """Create a new user synced from Feishu."""
        db_obj = User(
            username=username,
            email=email,
            full_name=full_name,
            hashed_password=hashed_password,
            feishu_open_id=feishu_open_id,
            feishu_union_id=feishu_union_id,
            employee_id=employee_no,
            feishu_sync_at=now_shanghai(),
            is_feishu_user=True,
            is_active=True,
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)

        viewer_role_result = await db.execute(select(Role).where(Role.name == "viewer"))
        viewer_role = viewer_role_result.scalar_one_or_none()
        if viewer_role:
            db_obj.roles.append(viewer_role)

        if role_ids:
            all_role_ids = list(set(role_ids) - {viewer_role.id} if viewer_role else set(role_ids))
            if all_role_ids:
                additional_roles = await self._get_roles_by_ids(db, all_role_ids)
                for role in additional_roles:
                    if role not in db_obj.roles:
                        db_obj.roles.append(role)

        await db.commit()
        await db.refresh(db_obj)

        return db_obj

    async def update_feishu_user(
        self,
        db: AsyncSession,
        *,
        user: User,
        full_name: str | None = None,
        email: str | None = None,
        mobile: str | None = None,
        employee_no: str | None = None,
        hashed_password: str | None = None,
    ) -> User:
        """Update a Feishu-synced user's info."""
        if full_name is not None:
            user.full_name = full_name
        if email is not None:
            user.email = email
        if employee_no is not None and user.employee_id != employee_no:
            user.employee_id = employee_no
        if hashed_password is not None:
            user.hashed_password = hashed_password
        user.feishu_sync_at = now_shanghai()

        await db.commit()
        await db.refresh(user)
        return user

    async def delete_feishu_user(self, db: AsyncSession, *, user: User) -> None:
        """Delete a Feishu-synced user."""
        await db.delete(user)
        await db.commit()

    async def update(self, db: AsyncSession, *, db_obj: User, obj_in: UserUpdate) -> User:
        """Update user."""
        update_data = obj_in.model_dump(exclude_unset=True)

        if "password" in update_data and update_data["password"]:
            update_data["hashed_password"] = get_password_hash(update_data.pop("password"))

        role_ids = update_data.pop("role_ids", None)

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        if role_ids is not None:
            roles = await self._get_roles_by_ids(db, role_ids)
            db_obj.roles = roles

        await db.commit()
        await db.refresh(db_obj)
        return db_obj


crud_user = CRUDUser(User)
