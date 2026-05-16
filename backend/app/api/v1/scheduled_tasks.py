from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import distinct, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_permissions
from app.core.audit import audit_log
from app.core.exceptions import NotFoundError
from app.crud.crud_scheduled_task import crud_scheduled_task
from app.crud.crud_system_config import crud_system_config
from app.models.scheduled_task import ScheduledTask
from app.models.user import User
from app.scheduler import (
    remove_scheduler_job,
    run_task_manually,
    update_scheduler_job,
)
from app.schemas.scheduled_task import (
    ScheduledTaskListResponse,
    ScheduledTaskResponse,
    ScheduledTaskUpdate,
    TaskExecutionLogListResponse,
    TaskRunResponse,
)

router = APIRouter(prefix="/scheduled-tasks", tags=["定时任务"])


@router.get("", response_model=ScheduledTaskListResponse)
async def list_scheduled_tasks(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    name: str | None = Query(None),
    category: str | None = Query(None),
    is_enabled: bool | None = Query(None),
    trigger_type: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: None = Depends(require_permissions(["ops:read"])),
):
    items, total = await crud_scheduled_task.get_multi(
        db,
        skip=skip,
        limit=limit,
        name=name,
        category=category,
        is_enabled=is_enabled,
        trigger_type=trigger_type,
    )
    return {"total": total, "items": items}


@router.get("/task-names", response_model=list[str])
async def get_task_names(
    db: AsyncSession = Depends(get_db),
    current_user: None = Depends(require_permissions(["ops:read"])),
):
    result = await db.execute(select(distinct(ScheduledTask.name)).order_by(ScheduledTask.name))
    return [row[0] for row in result.all()]


@router.get("/{task_id}", response_model=ScheduledTaskResponse)
async def get_scheduled_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: None = Depends(require_permissions(["ops:read"])),
):
    task = await crud_scheduled_task.get_by_task_id(db, task_id)
    if not task:
        raise NotFoundError(detail=f"Scheduled task '{task_id}' not found")
    return task


@router.put("/{task_id}", response_model=ScheduledTaskResponse)
@audit_log(operation_type="UPDATE", module="scheduled_task", object_type="ScheduledTask")
async def update_scheduled_task(
    request: Request,
    task_id: str,
    obj_in: ScheduledTaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: None = Depends(require_permissions(["ops:write"])),
):
    task = await crud_scheduled_task.get_by_task_id(db, task_id)
    if not task:
        raise NotFoundError(detail=f"Scheduled task '{task_id}' not found")

    task = await crud_scheduled_task.update(db, db_obj=task, obj_in=obj_in)

    if obj_in.name is not None:
        await crud_system_config.upsert_by_key(
            db,
            key=f"scheduler.task_mapping.{task_id}",
            value=task.task_function,
            group="scheduler",
            description=f"定时任务「{task.name}」对应的代码函数路径",
        )

    if task.is_enabled:
        update_scheduler_job(task_id)
    else:
        remove_scheduler_job(task_id)

    return task


@router.post("/{task_id}/run", response_model=TaskRunResponse)
@audit_log(operation_type="RUN", module="scheduled_task", object_type="ScheduledTask")
async def run_scheduled_task(
    request: Request,
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["ops:write"])),
):
    task = await crud_scheduled_task.get_by_task_id(db, task_id)
    if not task:
        raise NotFoundError(detail=f"Scheduled task '{task_id}' not found")

    result = await run_task_manually(task_id, triggered_by=current_user.username)
    return result


@router.get("/{task_id}/logs", response_model=TaskExecutionLogListResponse)
async def get_scheduled_task_logs(
    task_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: None = Depends(require_permissions(["ops:read"])),
):
    task = await crud_scheduled_task.get_by_task_id(db, task_id)
    if not task:
        raise NotFoundError(detail=f"Scheduled task '{task_id}' not found")

    items, total = await crud_scheduled_task.get_execution_logs(
        db, task_id, skip=skip, limit=limit, status=status
    )
    return {"total": total, "items": items}
