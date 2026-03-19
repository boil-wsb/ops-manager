"""
IT Feedback API endpoints.
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.api.deps import get_db
from app.models.it_feedback import ITFeedback
from app.schemas.it_feedback import (
    ITFeedbackCreate,
    ITFeedbackResponse,
    ITFeedbackListResponse,
)


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    if request.client:
        return request.client.host
    return "unknown"


router = APIRouter(prefix="/it-feedback")


@router.post("", response_model=ITFeedbackResponse)
async def create_feedback(
    feedback_in: ITFeedbackCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    client_ip = get_client_ip(request)
    feedback = ITFeedback(
        computer_type=feedback_in.computer_type,
        usage_years=feedback_in.usage_years,
        lag_level=feedback_in.lag_level,
        lag_scenarios=feedback_in.lag_scenarios,
        description=feedback_in.description,
        contact=feedback_in.contact,
        client_ip=client_ip,
        status=feedback_in.status,
    )
    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)
    
    return ITFeedbackResponse.model_validate(feedback)


@router.get("", response_model=ITFeedbackListResponse)
async def list_feedback(
    status: Optional[str] = None,
    lag_level: Optional[str] = None,
    page: int = Query(1, ge=1, le=100),
    page_size: int = Query(10, ge=10, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(ITFeedback)
    
    if status:
        query = query.where(ITFeedback.status == status)
    if lag_level:
        query = query.where(ITFeedback.lag_level == lag_level)
    
    query = query.order_by(ITFeedback.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    total_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(total_query)).scalar() or 0
    
    items = (await db.execute(query)).scalars().all()
    
    return ITFeedbackListResponse(
        total=total,
        items=[ITFeedbackResponse.model_validate(item) for item in items],
    )


@router.get("/{feedback_id}", response_model=ITFeedbackResponse)
async def get_feedback(
    feedback_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ITFeedback).where(ITFeedback.id == feedback_id)
    )
    feedback = result.scalar_one_or_none()
    
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    
    return ITFeedbackResponse.model_validate(feedback)


@router.put("/{feedback_id}/resolve")
async def resolve_feedback(
    feedback_id: int,
    resolved_by: str,
    notes: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ITFeedback).where(ITFeedback.id == feedback_id)
    )
    feedback = result.scalar_one_or_none()
    
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    
    feedback.status = "resolved"
    feedback.resolved_at = datetime.utcnow()
    feedback.resolved_by = resolved_by
    if notes:
        feedback.notes = notes
    
    await db.commit()
    await db.refresh(feedback)
    
    return ITFeedbackResponse.model_validate(feedback)


@router.delete("/{feedback_id}")
async def delete_feedback(
    feedback_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ITFeedback).where(ITFeedback.id == feedback_id)
    )
    feedback = result.scalar_one_or_none()
    
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    
    await db.delete(feedback)
    await db.commit()
    
    return {"message": "Feedback deleted successfully"}
