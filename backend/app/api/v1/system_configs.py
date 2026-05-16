from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_permissions
from app.core.audit import audit_log
from app.core.exceptions import NotFoundError
from app.crud.crud_system_config import crud_system_config
from app.schemas.system_config import (
    SystemConfigCreate,
    SystemConfigListResponse,
    SystemConfigResponse,
    SystemConfigUpdate,
)

router = APIRouter(prefix="/system-configs", tags=["系统配置"])


@router.get("", response_model=SystemConfigListResponse)
async def list_system_configs(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    group: str | None = Query(None),
    key: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: None = Depends(require_permissions(["setting:read"])),
):
    items, total = await crud_system_config.get_multi(
        db, skip=skip, limit=limit, group=group, key=key
    )
    return {"total": total, "items": items}


@router.get("/groups", response_model=list[str])
async def list_config_groups(
    db: AsyncSession = Depends(get_db),
    current_user: None = Depends(require_permissions(["setting:read"])),
):
    from sqlalchemy import distinct, select

    from app.models.system_config import SystemConfig

    result = await db.execute(select(distinct(SystemConfig.group)).order_by(SystemConfig.group))
    return [row[0] for row in result.all()]


@router.get("/{config_key}", response_model=SystemConfigResponse)
async def get_system_config(
    config_key: str,
    db: AsyncSession = Depends(get_db),
    current_user: None = Depends(require_permissions(["setting:read"])),
):
    config = await crud_system_config.get_by_key(db, config_key)
    if not config:
        raise NotFoundError(detail=f"System config '{config_key}' not found")
    return config


@router.post("", response_model=SystemConfigResponse)
@audit_log(operation_type="CREATE", module="system_config", object_type="SystemConfig")
async def create_system_config(
    request: Request,
    obj_in: SystemConfigCreate,
    db: AsyncSession = Depends(get_db),
    current_user: None = Depends(require_permissions(["setting:update"])),
):
    existing = await crud_system_config.get_by_key(db, obj_in.key)
    if existing:
        from app.core.exceptions import ConflictError

        raise ConflictError(detail=f"System config '{obj_in.key}' already exists")
    return await crud_system_config.create(db, obj_in=obj_in)


@router.put("/{config_key}", response_model=SystemConfigResponse)
@audit_log(operation_type="UPDATE", module="system_config", object_type="SystemConfig")
async def update_system_config(
    request: Request,
    config_key: str,
    obj_in: SystemConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: None = Depends(require_permissions(["setting:update"])),
):
    config = await crud_system_config.get_by_key(db, config_key)
    if not config:
        raise NotFoundError(detail=f"System config '{config_key}' not found")
    return await crud_system_config.update(db, db_obj=config, obj_in=obj_in)


@router.delete("/{config_key}")
@audit_log(operation_type="DELETE", module="system_config", object_type="SystemConfig")
async def delete_system_config(
    request: Request,
    config_key: str,
    db: AsyncSession = Depends(get_db),
    current_user: None = Depends(require_permissions(["setting:update"])),
):
    deleted = await crud_system_config.delete(db, key=config_key)
    if not deleted:
        raise NotFoundError(detail=f"System config '{config_key}' not found")
    return {"message": "Deleted successfully"}
