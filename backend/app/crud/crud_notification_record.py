"""
CRUD operations for Notification Record.
"""
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.notification_record import NotificationRecord
from app.schemas.notification_record import (
    NotificationRecordCreate,
    NotificationRecordUpdate,
)


class CRUDNotificationRecord(CRUDBase):
    """CRUD operations for Notification Record."""

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 10,
        user: str | None = None,
        success: bool | None = None,
    ) -> tuple[int, list[NotificationRecord]]:
        """Get multiple notification records with filtering and pagination."""
        query = select(NotificationRecord)

        if user:
            query = query.where(NotificationRecord.user.ilike(f"%{user}%"))
        if success is not None:
            query = query.where(NotificationRecord.success == success)

        query = query.order_by(NotificationRecord.created_at.desc())

        total_query = select(func.count()).select_from(query.subquery())
        total = (await db.execute(total_query)).scalar() or 0

        query = query.offset(skip).limit(limit)
        items = (await db.execute(query)).scalars().all()

        return total, list(items)

    async def create(
        self,
        db: AsyncSession,
        *,
        obj_in: NotificationRecordCreate,
    ) -> NotificationRecord:
        """Create a new notification record."""
        db_obj = NotificationRecord(
            user=obj_in.user,
            matched_user=obj_in.matched_user,
            feishu_open_id=obj_in.feishu_open_id,
            card_content=obj_in.card_content,
            success=obj_in.success,
            error=obj_in.error,
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        *,
        record_id: int,
        obj_in: NotificationRecordUpdate,
    ) -> NotificationRecord | None:
        """Update an existing notification record."""
        update_data = obj_in.model_dump(exclude_unset=True)
        if not update_data:
            result = await db.execute(
                select(NotificationRecord).where(NotificationRecord.id == record_id)
            )
            return result.scalar_one_or_none()

        if "success" in update_data and update_data["success"] is None:
            del update_data["success"]

        stmt = (
            update(NotificationRecord)
            .where(NotificationRecord.id == record_id)
            .values(**update_data)
            .returning(NotificationRecord)
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.scalar_one_or_none()

    async def delete(
        self,
        db: AsyncSession,
        *,
        record_id: int,
    ) -> bool:
        """Delete a notification record."""
        result = await db.execute(
            select(NotificationRecord).where(NotificationRecord.id == record_id)
        )
        record = result.scalar_one_or_none()
        if not record:
            return False
        await db.delete(record)
        await db.commit()
        return True


notification_record = CRUDNotificationRecord(NotificationRecord)
