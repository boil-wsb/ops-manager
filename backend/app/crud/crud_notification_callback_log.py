from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification_callback_log import NotificationCallbackLog


class CRUDNotificationCallbackLog:
    async def get_multi(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        notification_record_id: int | None = None,
    ) -> tuple[int, list[NotificationCallbackLog]]:
        query = select(NotificationCallbackLog)

        if status:
            query = query.where(NotificationCallbackLog.status == status)
        if notification_record_id:
            query = query.where(
                NotificationCallbackLog.notification_record_id == notification_record_id
            )

        query = query.order_by(NotificationCallbackLog.created_at.desc())

        total_query = select(func.count()).select_from(query.subquery())
        total = (await db.execute(total_query)).scalar() or 0

        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        items = (await db.execute(query)).scalars().all()

        return total, list(items)

    async def create(
        self,
        db: AsyncSession,
        *,
        notification_record_id: int | None = None,
        callback_url: str = "",
        request_body: dict | None = None,
        response_status: int | None = None,
        response_body: str | None = None,
        status: str = "pending",
        error_message: str | None = None,
    ) -> NotificationCallbackLog:
        db_obj = NotificationCallbackLog(
            notification_record_id=notification_record_id,
            callback_url=callback_url,
            request_body=request_body,
            response_status=response_status,
            response_body=response_body,
            status=status,
            error_message=error_message,
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj


notification_callback_log = CRUDNotificationCallbackLog()
