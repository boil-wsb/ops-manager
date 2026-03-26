"""
CRUD operations for PC Client Version.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.pc_client_version import PCClientVersion


class CRUDPCClientVersion(CRUDBase):
    """CRUD operations for PCClientVersion."""

    async def get_active_version(self, db: AsyncSession) -> PCClientVersion | None:
        """Get the latest active version."""
        result = await db.execute(
            select(PCClientVersion)
            .where(PCClientVersion.is_active)
            .order_by(PCClientVersion.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_version_by_version_string(
        self, db: AsyncSession, version: str
    ) -> PCClientVersion | None:
        """Get version by version string."""
        result = await db.execute(
            select(PCClientVersion).where(PCClientVersion.version == version)
        )
        return result.scalar_one_or_none()

    async def get_all_versions(
        self, db: AsyncSession, skip: int = 0, limit: int = 100
    ) -> list[PCClientVersion]:
        """Get all versions with pagination."""
        result = await db.execute(
            select(PCClientVersion)
            .order_by(PCClientVersion.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())


crud_pc_client_version = CRUDPCClientVersion(PCClientVersion)
