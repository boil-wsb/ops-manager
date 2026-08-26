"""
User IP binding CRUD operations.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tz import now_shanghai
from app.models.user_ip_binding import UserIpBinding


class CRUDUserIpBinding:
    """User IP binding CRUD operations."""

    async def get_by_user_id(self, db: AsyncSession, *, user_id: int) -> UserIpBinding | None:
        """Get binding by user ID."""
        result = await db.execute(select(UserIpBinding).where(UserIpBinding.user_id == user_id))
        return result.scalar_one_or_none()

    async def get_by_ip(self, db: AsyncSession, *, ip_address: str) -> UserIpBinding | None:
        """Get binding by IP address."""
        result = await db.execute(
            select(UserIpBinding).where(UserIpBinding.ip_address == ip_address)
        )
        return result.scalar_one_or_none()

    async def create_binding(
        self, db: AsyncSession, *, user_id: int, ip_address: str
    ) -> UserIpBinding:
        """Create a new IP binding for a user."""
        binding = UserIpBinding(
            user_id=user_id,
            ip_address=ip_address,
            bound_at=now_shanghai(),
        )
        db.add(binding)
        await db.commit()
        await db.refresh(binding)
        return binding

    async def delete_binding(self, db: AsyncSession, *, user_id: int) -> bool:
        """Delete (unbind) a user's IP binding. Returns True if deleted."""
        binding = await self.get_by_user_id(db, user_id=user_id)
        if binding:
            await db.delete(binding)
            await db.commit()
            return True
        return False

    async def get_all(
        self, db: AsyncSession, *, skip: int = 0, limit: int = 100
    ) -> list[UserIpBinding]:
        """Get all IP bindings (for admin management)."""
        result = await db.execute(select(UserIpBinding).offset(skip).limit(limit))
        return list(result.scalars().all())


crud_user_ip_binding = CRUDUserIpBinding()
