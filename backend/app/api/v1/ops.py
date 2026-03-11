"""
Operations management API routes.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_permissions
from app.crud.base import CRUDBase
from app.models.ops import Deployment, InspectionTask, InspectionReport, Certificate, DNSRecord
from app.schemas.ops import (
    DeploymentCreate, DeploymentUpdate, DeploymentResponse, DeploymentListResponse,
    InspectionTaskCreate, InspectionTaskUpdate, InspectionTaskResponse,
    InspectionReportResponse,
    CertificateCreate, CertificateUpdate, CertificateResponse,
    DNSRecordCreate, DNSRecordUpdate, DNSRecordResponse
)
from app.core.exceptions import NotFoundError

router = APIRouter()

# CRUD instances
crud_deployment = CRUDBase(Deployment)
crud_inspection_task = CRUDBase(InspectionTask)
crud_inspection_report = CRUDBase(InspectionReport)
crud_certificate = CRUDBase(Certificate)
crud_dns = CRUDBase(DNSRecord)


# Deployment routes
@router.get("/deployments", response_model=DeploymentListResponse)
async def list_deployments(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    project: Optional[str] = Query(None),
    environment: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user = require_permissions(["ops:read"])
):
    """List all deployments with filters."""
    query = select(Deployment)
    
    # Apply filters
    filters = []
    if project:
        filters.append(Deployment.project_name.ilike(f"%{project}%"))
    if environment:
        filters.append(Deployment.environment == environment)
    if status:
        filters.append(Deployment.status == status)
    
    if filters:
        query = query.where(and_(*filters))
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()
    
    # Apply pagination
    query = query.offset(skip).limit(limit).order_by(Deployment.created_at.desc())
    result = await db.execute(query)
    items = result.scalars().all()
    
    return {"total": total, "items": items}


@router.post("/deployments", response_model=DeploymentResponse, status_code=status.HTTP_201_CREATED)
async def create_deployment(
    obj_in: DeploymentCreate,
    db: AsyncSession = Depends(get_db),
    current_user = require_permissions(["ops:write"])
):
    """Create a new deployment record."""
    deployment = await crud_deployment.create(
        db,
        obj_in=obj_in,
    )
    deployment.deployer_id = current_user.id
    await db.commit()
    await db.refresh(deployment)
    return deployment


@router.get("/deployments/{deployment_id}", response_model=DeploymentResponse)
async def get_deployment(
    deployment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = require_permissions(["ops:read"])
):
    """Get deployment by ID."""
    deployment = await crud_deployment.get(db, id=deployment_id)
    if not deployment:
        raise NotFoundError(detail=f"Deployment with ID {deployment_id} not found")
    return deployment


@router.put("/deployments/{deployment_id}", response_model=DeploymentResponse)
async def update_deployment(
    deployment_id: int,
    obj_in: DeploymentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = require_permissions(["ops:write"])
):
    """Update deployment."""
    deployment = await crud_deployment.get(db, id=deployment_id)
    if not deployment:
        raise NotFoundError(detail=f"Deployment with ID {deployment_id} not found")
    
    deployment = await crud_deployment.update(db, db_obj=deployment, obj_in=obj_in)
    return deployment


# Inspection routes
@router.get("/inspections/tasks", response_model=List[InspectionTaskResponse])
async def list_inspection_tasks(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user = require_permissions(["ops:read"])
):
    """List all inspection tasks."""
    tasks = await crud_inspection_task.get_multi(db, skip=skip, limit=limit)
    return tasks


@router.post("/inspections/tasks", response_model=InspectionTaskResponse, status_code=status.HTTP_201_CREATED)
async def create_inspection_task(
    obj_in: InspectionTaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user = require_permissions(["ops:write"])
):
    """Create a new inspection task."""
    task = await crud_inspection_task.create(db, obj_in=obj_in)
    return task


@router.get("/inspections/tasks/{task_id}", response_model=InspectionTaskResponse)
async def get_inspection_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = require_permissions(["ops:read"])
):
    """Get inspection task by ID."""
    task = await crud_inspection_task.get(db, id=task_id)
    if not task:
        raise NotFoundError(detail=f"Inspection task with ID {task_id} not found")
    return task


@router.put("/inspections/tasks/{task_id}", response_model=InspectionTaskResponse)
async def update_inspection_task(
    task_id: int,
    obj_in: InspectionTaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = require_permissions(["ops:write"])
):
    """Update inspection task."""
    task = await crud_inspection_task.get(db, id=task_id)
    if not task:
        raise NotFoundError(detail=f"Inspection task with ID {task_id} not found")
    
    task = await crud_inspection_task.update(db, db_obj=task, obj_in=obj_in)
    return task


@router.delete("/inspections/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_inspection_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = require_permissions(["ops:delete"])
):
    """Delete inspection task."""
    task = await crud_inspection_task.get(db, id=task_id)
    if not task:
        raise NotFoundError(detail=f"Inspection task with ID {task_id} not found")
    
    await crud_inspection_task.delete(db, id=task_id)
    return None


@router.get("/inspections/reports", response_model=List[InspectionReportResponse])
async def list_inspection_reports(
    task_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user = require_permissions(["ops:read"])
):
    """List inspection reports."""
    query = select(InspectionReport)
    if task_id:
        query = query.where(InspectionReport.task_id == task_id)
    
    query = query.offset(skip).limit(limit).order_by(InspectionReport.created_at.desc())
    result = await db.execute(query)
    reports = result.scalars().all()
    return reports


@router.get("/inspections/reports/{report_id}", response_model=InspectionReportResponse)
async def get_inspection_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = require_permissions(["ops:read"])
):
    """Get inspection report by ID."""
    report = await crud_inspection_report.get(db, id=report_id)
    if not report:
        raise NotFoundError(detail=f"Inspection report with ID {report_id} not found")
    return report


# Certificate routes
@router.get("/certificates", response_model=List[CertificateResponse])
async def list_certificates(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    expiring_soon: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user = require_permissions(["ops:read"])
):
    """List all certificates."""
    query = select(Certificate)
    
    if status:
        query = query.where(Certificate.status == status)
    
    if expiring_soon:
        query = query.where(Certificate.days_until_expiry <= Certificate.alert_threshold_days)
    
    query = query.offset(skip).limit(limit).order_by(Certificate.valid_until.asc())
    result = await db.execute(query)
    certificates = result.scalars().all()
    return certificates


@router.post("/certificates", response_model=CertificateResponse, status_code=status.HTTP_201_CREATED)
async def create_certificate(
    obj_in: CertificateCreate,
    db: AsyncSession = Depends(get_db),
    current_user = require_permissions(["ops:write"])
):
    """Create a new certificate."""
    # Calculate days until expiry
    from datetime import datetime
    days_until_expiry = (obj_in.valid_until - datetime.utcnow()).days
    
    cert_data = obj_in.model_dump()
    cert_data["days_until_expiry"] = max(0, days_until_expiry)
    
    # Determine status
    if days_until_expiry <= 0:
        cert_data["status"] = "expired"
    elif days_until_expiry <= obj_in.alert_threshold_days:
        cert_data["status"] = "expiring"
    else:
        cert_data["status"] = "active"
    
    certificate = await crud_certificate.create(db, obj_in=CertificateCreate(**cert_data))
    return certificate


@router.get("/certificates/{cert_id}", response_model=CertificateResponse)
async def get_certificate(
    cert_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = require_permissions(["ops:read"])
):
    """Get certificate by ID."""
    certificate = await crud_certificate.get(db, id=cert_id)
    if not certificate:
        raise NotFoundError(detail=f"Certificate with ID {cert_id} not found")
    return certificate


@router.put("/certificates/{cert_id}", response_model=CertificateResponse)
async def update_certificate(
    cert_id: int,
    obj_in: CertificateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = require_permissions(["ops:write"])
):
    """Update certificate."""
    certificate = await crud_certificate.get(db, id=cert_id)
    if not certificate:
        raise NotFoundError(detail=f"Certificate with ID {cert_id} not found")
    
    certificate = await crud_certificate.update(db, db_obj=certificate, obj_in=obj_in)
    return certificate


@router.delete("/certificates/{cert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_certificate(
    cert_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = require_permissions(["ops:delete"])
):
    """Delete certificate."""
    certificate = await crud_certificate.get(db, id=cert_id)
    if not certificate:
        raise NotFoundError(detail=f"Certificate with ID {cert_id} not found")
    
    await crud_certificate.delete(db, id=cert_id)
    return None


# DNS routes
@router.get("/dns", response_model=List[DNSRecordResponse])
async def list_dns_records(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    domain: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user = require_permissions(["ops:read"])
):
    """List all DNS records."""
    query = select(DNSRecord)
    
    if domain:
        query = query.where(DNSRecord.domain.ilike(f"%{domain}%"))
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    records = result.scalars().all()
    return records


@router.post("/dns", response_model=DNSRecordResponse, status_code=status.HTTP_201_CREATED)
async def create_dns_record(
    obj_in: DNSRecordCreate,
    db: AsyncSession = Depends(get_db),
    current_user = require_permissions(["ops:write"])
):
    """Create a new DNS record."""
    record = await crud_dns.create(db, obj_in=obj_in)
    return record


@router.get("/dns/{record_id}", response_model=DNSRecordResponse)
async def get_dns_record(
    record_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = require_permissions(["ops:read"])
):
    """Get DNS record by ID."""
    record = await crud_dns.get(db, id=record_id)
    if not record:
        raise NotFoundError(detail=f"DNS record with ID {record_id} not found")
    return record


@router.put("/dns/{record_id}", response_model=DNSRecordResponse)
async def update_dns_record(
    record_id: int,
    obj_in: DNSRecordUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = require_permissions(["ops:write"])
):
    """Update DNS record."""
    record = await crud_dns.get(db, id=record_id)
    if not record:
        raise NotFoundError(detail=f"DNS record with ID {record_id} not found")
    
    record = await crud_dns.update(db, db_obj=record, obj_in=obj_in)
    return record


@router.delete("/dns/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dns_record(
    record_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = require_permissions(["ops:delete"])
):
    """Delete DNS record."""
    record = await crud_dns.get(db, id=record_id)
    if not record:
        raise NotFoundError(detail=f"DNS record with ID {record_id} not found")
    
    await crud_dns.delete(db, id=record_id)
    return None
