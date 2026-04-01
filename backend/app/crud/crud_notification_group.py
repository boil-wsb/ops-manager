"""
CRUD operations for notification groups.
"""
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase
from app.models.notification_group import NotificationGroup
from app.models.user import User
from app.schemas.notification_group import NotificationGroupCreate, NotificationGroupUpdate


class CRUDNotificationGroup(CRUDBase[NotificationGroup, NotificationGroupCreate, NotificationGroupUpdate]):
    """CRUD operations for notification groups."""

    async def get_multi_with_filter(
        self,
        db: AsyncSession,
        *,
        notification_type: str | None = None,
        is_active: bool | None = None,
        skip: int = 0,
        limit: int = 100
    ) -> list[NotificationGroup]:
        """Get multiple notification groups with filters."""
        conditions = []
        if notification_type is not None:
            conditions.append(NotificationGroup.notification_type == notification_type)
        if is_active is not None:
            conditions.append(NotificationGroup.is_active == is_active)

        query = (
            select(NotificationGroup)
            .options(selectinload(NotificationGroup.members))
        )
        if conditions:
            query = query.where(and_(*conditions))

        result = await db.execute(
            query.order_by(NotificationGroup.id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def count_with_filter(
        self,
        db: AsyncSession,
        *,
        notification_type: str | None = None,
        is_active: bool | None = None
    ) -> int:
        """Count notification groups with filters."""
        from sqlalchemy import func

        conditions = []
        if notification_type is not None:
            conditions.append(NotificationGroup.notification_type == notification_type)
        if is_active is not None:
            conditions.append(NotificationGroup.is_active == is_active)

        query = select(func.count(NotificationGroup.id))
        if conditions:
            query = query.where(and_(*conditions))

        result = await db.execute(query)
        return result.scalar() or 0

    async def get_with_members(
        self,
        db: AsyncSession,
        *,
        id: int
    ) -> NotificationGroup | None:
        """Get a notification group by ID with members loaded."""
        result = await db.execute(
            select(NotificationGroup)
            .options(selectinload(NotificationGroup.members))
            .where(NotificationGroup.id == id)
        )
        return result.scalar_one_or_none()

    async def get_by_notification_type(
        self,
        db: AsyncSession,
        notification_type: str
    ) -> list[NotificationGroup]:
        """Get active notification groups by notification type."""
        result = await db.execute(
            select(NotificationGroup)
            .options(selectinload(NotificationGroup.members))
            .where(
                and_(
                    NotificationGroup.notification_type == notification_type,
                    NotificationGroup.is_active
                )
            )
        )
        return result.scalars().all()

    async def get_group_member_feishu_ids(
        self,
        db: AsyncSession,
        group_id: int
    ) -> list[str]:
        """Get feishu open_ids of all members in a notification group."""
        result = await db.execute(
            select(NotificationGroup)
            .options(selectinload(NotificationGroup.members))
            .where(NotificationGroup.id == group_id)
        )
        group = result.scalar_one_or_none()
        if not group:
            return []

        feishu_ids = []
        for user in group.members:
            if user.feishu_open_id:
                feishu_ids.append(user.feishu_open_id)
        return feishu_ids

    async def add_member(
        self,
        db: AsyncSession,
        *,
        group_id: int,
        user_id: int
    ) -> NotificationGroup | None:
        """Add a user to a notification group."""
        group = await self.get_with_members(db, id=group_id)
        if not group:
            return None

        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return None

        if user not in group.members:
            group.members.append(user)
            await db.commit()
            await db.refresh(group)

        return group

    async def remove_member(
        self,
        db: AsyncSession,
        *,
        group_id: int,
        user_id: int
    ) -> NotificationGroup | None:
        """Remove a user from a notification group."""
        group = await self.get_with_members(db, id=group_id)
        if not group:
            return None

        group.members = [m for m in group.members if m.id != user_id]
        await db.commit()
        await db.refresh(group)

        return group


notification_group = CRUDNotificationGroup(NotificationGroup)
