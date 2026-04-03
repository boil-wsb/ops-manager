"""
Alert silence rules API routes.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.exceptions import NotFoundError
from app.crud.crud_alert import crud_alert_silence
from app.schemas.alert import AlertSilenceCreate, AlertSilenceUpdate, AlertSilenceResponse

router = APIRouter()


@router.get("/silences", response_model=list[AlertSilenceResponse])
async def get_silences(
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
):
    """Get all alert silence rules."""
    silences = await crud_alert_silence.get_multi(db, skip=skip, limit=limit)
    return silences


@router.post("/silences", response_model=AlertSilenceResponse, status_code=201)
async def create_silence(
    silence_in: AlertSilenceCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new alert silence rule."""
    silence = await crud_alert_silence.create(db, obj_in=silence_in)
    return silence


@router.delete("/silences/{silence_id}", status_code=204)
async def delete_silence(
    silence_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete an alert silence rule."""
    silence = await crud_alert_silence.get(db, id=silence_id)
    if not silence:
        raise NotFoundError(detail=f"Alert silence with ID {silence_id} not found")
    await crud_alert_silence.delete(db, id=silence_id)
    return None
