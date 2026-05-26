from datetime import datetime

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tz import now_shanghai
from app.models.scheduled_task import ScheduledTask, TaskExecutionLog
from app.schemas.scheduled_task import ScheduledTaskUpdate


class CRUDScheduledTask:
    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 20,
        name: str | None = None,
        category: str | None = None,
        is_enabled: bool | None = None,
        trigger_type: str | None = None,
    ) -> tuple[list[ScheduledTask], int]:
        query = select(ScheduledTask)
        count_query = select(func.count(ScheduledTask.id))

        filters = []
        if name:
            filters.append(ScheduledTask.name.ilike(f"%{name}%"))
        if category:
            filters.append(ScheduledTask.category == category)
        if is_enabled is not None:
            filters.append(ScheduledTask.is_enabled == is_enabled)
        if trigger_type:
            filters.append(ScheduledTask.trigger_type == trigger_type)

        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))

        total_result = await db.execute(count_query)
        total = total_result.scalar()

        query = query.offset(skip).limit(limit).order_by(ScheduledTask.id.asc())
        result = await db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def get_by_task_id(self, db: AsyncSession, task_id: str) -> ScheduledTask | None:
        result = await db.execute(select(ScheduledTask).where(ScheduledTask.task_id == task_id))
        return result.scalar_one_or_none()

    async def get_execution_logs(
        self,
        db: AsyncSession,
        task_id: str,
        *,
        skip: int = 0,
        limit: int = 20,
        status: str | None = None,
    ) -> tuple[list[TaskExecutionLog], int]:
        query = select(TaskExecutionLog).where(TaskExecutionLog.task_id == task_id)
        count_query = select(func.count(TaskExecutionLog.id)).where(
            TaskExecutionLog.task_id == task_id
        )

        if status:
            query = query.where(TaskExecutionLog.status == status)
            count_query = count_query.where(TaskExecutionLog.status == status)

        total_result = await db.execute(count_query)
        total = total_result.scalar()

        query = (
            query.offset(skip)
            .limit(limit)
            .order_by(TaskExecutionLog.started_at.desc())
        )
        result = await db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def upsert_by_task_id(
        self,
        db: AsyncSession,
        *,
        task_id: str,
        name: str,
        task_function: str,
        trigger_type: str,
        trigger_config: dict,
        category: str,
        description: str | None = None,
    ) -> ScheduledTask:
        existing = await self.get_by_task_id(db, task_id)
        if existing:
            return existing

        db_obj = ScheduledTask(
            task_id=task_id,
            name=name,
            task_function=task_function,
            trigger_type=trigger_type,
            trigger_config=trigger_config,
            category=category,
            description=description,
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: ScheduledTask,
        obj_in: ScheduledTaskUpdate,
    ) -> ScheduledTask:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def create_execution_log(
        self,
        db: AsyncSession,
        *,
        task_id: str,
        status: str,
        started_at: datetime,
        finished_at: datetime | None = None,
        duration: float | None = None,
        error_message: str | None = None,
        result_summary: str | None = None,
        trigger_type: str = "scheduled",
        triggered_by: str | None = None,
    ) -> TaskExecutionLog:
        db_obj = TaskExecutionLog(
            task_id=task_id,
            status=status,
            started_at=started_at,
            finished_at=finished_at,
            duration=duration,
            error_message=error_message,
            result_summary=result_summary,
            trigger_type=trigger_type,
            triggered_by=triggered_by,
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update_run_status(
        self,
        db: AsyncSession,
        *,
        task_id: str,
        status: str,
        duration: float,
        result_summary: str | None = None,
        error_message: str | None = None,
    ) -> ScheduledTask:
        db_obj = await self.get_by_task_id(db, task_id)
        if db_obj:
            db_obj.last_run_at = now_shanghai()
            db_obj.last_run_status = status
            db_obj.last_run_duration = duration
            db.add(db_obj)
            await db.commit()
            await db.refresh(db_obj)
        return db_obj


crud_scheduled_task = CRUDScheduledTask()
