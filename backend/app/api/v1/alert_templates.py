"""
Alert template API routes.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.exceptions import NotFoundError
from app.crud.crud_alert import crud_alert_template
from app.schemas.alert import (
    AlertTemplateCreate,
    AlertTemplatePreview,
    AlertTemplateResponse,
    AlertTemplateUpdate,
)

router = APIRouter()


@router.get("/templates", response_model=list[AlertTemplateResponse])
async def get_templates(
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
):
    """Get all alert templates."""
    templates = await crud_alert_template.get_multi(db, skip=skip, limit=limit)
    return templates


@router.post("/templates", response_model=AlertTemplateResponse, status_code=201)
async def create_template(
    template_in: AlertTemplateCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new alert template."""
    template = await crud_alert_template.create(db, obj_in=template_in)
    return template


@router.get("/templates/{template_id}", response_model=AlertTemplateResponse)
async def get_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific alert template."""
    template = await crud_alert_template.get(db, id=template_id)
    if not template:
        raise NotFoundError(detail=f"Alert template with ID {template_id} not found")
    return template


@router.put("/templates/{template_id}", response_model=AlertTemplateResponse)
async def update_template(
    template_id: int,
    template_in: AlertTemplateUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an alert template."""
    template = await crud_alert_template.get(db, id=template_id)
    if not template:
        raise NotFoundError(detail=f"Alert template with ID {template_id} not found")
    template = await crud_alert_template.update(db, db_obj=template, obj_in=template_in)
    return template


@router.delete("/templates/{template_id}", status_code=204)
async def delete_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete an alert template."""
    template = await crud_alert_template.get(db, id=template_id)
    if not template:
        raise NotFoundError(detail=f"Alert template with ID {template_id} not found")
    await crud_alert_template.delete(db, id=template_id)
    return None


@router.post("/templates/{template_id}/preview")
async def preview_template(
    template_id: int,
    preview_data: AlertTemplatePreview,
    db: AsyncSession = Depends(get_db),
):
    """Preview template rendering with provided data."""
    from app.services.alerts.alert_template import alert_template_service

    template = await crud_alert_template.get(db, id=template_id)
    if not template:
        raise NotFoundError(detail=f"Alert template with ID {template_id} not found")

    rendered = alert_template_service.render_template(
        template_body=template.body_template,
        alertname=preview_data.alertname,
        status=preview_data.status,
        severity=preview_data.severity,
        instance=preview_data.instance,
        description=preview_data.description,
        starts_at=preview_data.starts_at,
        labels=preview_data.labels,
        annotations=preview_data.annotations,
    )

    return {
        "rendered": rendered,
        "template_id": template_id,
    }
