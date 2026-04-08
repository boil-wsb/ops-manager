"""
Operations management API routes.
"""
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_permissions
from app.core.audit import audit_log
from app.core.exceptions import NotFoundError
from app.crud.base import CRUDBase
from app.models.ops import (
    Certificate,
    Deployment,
    DNSRecord,
    InspectionReport,
    InspectionTask,
)
from app.models.user import User
from app.schemas.ops import (
    CertificateCreate,
    CertificateResponse,
    CertificateSyncResponse,
    CertificateUpdate,
    DeploymentCreate,
    DeploymentListResponse,
    DeploymentResponse,
    DeploymentUpdate,
    DNSRecordCreate,
    DNSRecordResponse,
    DNSRecordUpdate,
    InspectionReportResponse,
    InspectionTaskCreate,
    InspectionTaskResponse,
    InspectionTaskUpdate,
)
from app.services.prometheus.client import get_prometheus_client

router = APIRouter(prefix="/ops")

crud_deployment = CRUDBase(Deployment)
crud_inspection_task = CRUDBase(InspectionTask)
crud_inspection_report = CRUDBase(InspectionReport)
crud_certificate = CRUDBase(Certificate)
crud_dns = CRUDBase(DNSRecord)


@router.get("/deployments", response_model=DeploymentListResponse)
async def list_deployments(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    project: str | None = Query(None),
    environment: str | None = Query(None),
    status: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: None = Depends(require_permissions(["ops:read"])),
):
    """List all deployments with filters."""
    query = select(Deployment)

    filters = []
    if project:
        filters.append(Deployment.project_name.ilike(f"%{project}%"))
    if environment:
        filters.append(Deployment.environment == environment)
    if status:
        filters.append(Deployment.status == status)

    if filters:
        query = query.where(and_(*filters))

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()

    query = query.offset(skip).limit(limit).order_by(Deployment.created_at.desc())
    result = await db.execute(query)
    items = result.scalars().all()

    return {"total": total, "items": items}


@router.post("/deployments", response_model=DeploymentResponse, status_code=status.HTTP_201_CREATED)
@audit_log(operation_type="CREATE", module="ops", object_type="Deployment")
async def create_deployment(
    request: Request,
    obj_in: DeploymentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["ops:write"])),
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
    current_user: None = Depends(require_permissions(["ops:read"])),
):
    """Get deployment by ID."""
    deployment = await crud_deployment.get(db, id=deployment_id)
    if not deployment:
        raise NotFoundError(detail=f"Deployment with ID {deployment_id} not found")
    return deployment


@router.put("/deployments/{deployment_id}", response_model=DeploymentResponse)
@audit_log(operation_type="UPDATE", module="ops", object_type="Deployment")
async def update_deployment(
    request: Request,
    deployment_id: int,
    obj_in: DeploymentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: None = Depends(require_permissions(["ops:write"])),
):
    """Update deployment."""
    deployment = await crud_deployment.get(db, id=deployment_id)
    if not deployment:
        raise NotFoundError(detail=f"Deployment with ID {deployment_id} not found")

    deployment = await crud_deployment.update(db, db_obj=deployment, obj_in=obj_in)
    return deployment


@router.get("/inspections/tasks", response_model=list[InspectionTaskResponse])
async def list_inspection_tasks(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: None = Depends(require_permissions(["ops:read"])),
):
    """List all inspection tasks."""
    tasks = await crud_inspection_task.get_multi(db, skip=skip, limit=limit)
    return tasks


@router.post("/inspections/tasks", response_model=InspectionTaskResponse, status_code=status.HTTP_201_CREATED)
@audit_log(operation_type="CREATE", module="ops", object_type="InspectionTask")
async def create_inspection_task(
    request: Request,
    obj_in: InspectionTaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: None = Depends(require_permissions(["ops:write"])),
):
    """Create a new inspection task."""
    task = await crud_inspection_task.create(db, obj_in=obj_in)
    return task


@router.get("/inspections/tasks/{task_id}", response_model=InspectionTaskResponse)
async def get_inspection_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: None = Depends(require_permissions(["ops:read"]))
):
    """Get inspection task by ID."""
    task = await crud_inspection_task.get(db, id=task_id)
    if not task:
        raise NotFoundError(detail=f"Inspection task with ID {task_id} not found")
    return task


@router.put("/inspections/tasks/{task_id}", response_model=InspectionTaskResponse)
@audit_log(operation_type="UPDATE", module="ops", object_type="InspectionTask")
async def update_inspection_task(
    request: Request,
    task_id: int,
    obj_in: InspectionTaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: None = Depends(require_permissions(["ops:write"]))
):
    """Update inspection task."""
    task = await crud_inspection_task.get(db, id=task_id)
    if not task:
        raise NotFoundError(detail=f"Inspection task with ID {task_id} not found")

    task = await crud_inspection_task.update(db, db_obj=task, obj_in=obj_in)
    return task


@router.delete("/inspections/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
@audit_log(operation_type="DELETE", module="ops", object_type="InspectionTask")
async def delete_inspection_task(
    request: Request,
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: None = Depends(require_permissions(["ops:delete"]))
):
    """Delete inspection task."""
    task = await crud_inspection_task.get(db, id=task_id)
    if not task:
        raise NotFoundError(detail=f"Inspection task with ID {task_id} not found")

    await crud_inspection_task.delete(db, id=task_id)
    return None


@router.get("/inspections/reports", response_model=list[InspectionReportResponse])
async def list_inspection_reports(
    task_id: int | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: None = Depends(require_permissions(["ops:read"]))
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
    current_user: None = Depends(require_permissions(["ops:read"]))
):
    """Get inspection report by ID."""
    report = await crud_inspection_report.get(db, id=report_id)
    if not report:
        raise NotFoundError(detail=f"Inspection report with ID {report_id} not found")
    return report


@router.get("/certificates", response_model=list[CertificateResponse])
async def list_certificates(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    expiring_soon: bool | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: None = Depends(require_permissions(["ops:read"]))
):
    """List all certificates."""
    query = select(Certificate)

    if status:
        query = query.where(Certificate.status == status)

    if expiring_soon is True:
        query = query.where(Certificate.days_until_expiry <= Certificate.alert_threshold_days)
    elif expiring_soon is False:
        query = query.where(Certificate.days_until_expiry > Certificate.alert_threshold_days)

    query = query.offset(skip).limit(limit).order_by(Certificate.valid_until.asc())
    result = await db.execute(query)
    certificates = result.scalars().all()
    return certificates


@router.post("/certificates", response_model=CertificateResponse, status_code=status.HTTP_201_CREATED)
@audit_log(operation_type="CREATE", module="ops", object_type="Certificate")
async def create_certificate(
    request: Request,
    obj_in: CertificateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: None = Depends(require_permissions(["ops:write"]))
):
    """Create a new certificate."""
    days_until_expiry = (obj_in.valid_until - datetime.utcnow()).days

    cert_data = obj_in.model_dump()
    cert_data["days_until_expiry"] = max(0, days_until_expiry)

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
    current_user: None = Depends(require_permissions(["ops:read"]))
):
    """Get certificate by ID."""
    certificate = await crud_certificate.get(db, id=cert_id)
    if not certificate:
        raise NotFoundError(detail=f"Certificate with ID {cert_id} not found")
    return certificate


@router.put("/certificates/{cert_id}", response_model=CertificateResponse)
@audit_log(operation_type="UPDATE", module="ops", object_type="Certificate")
async def update_certificate(
    request: Request,
    cert_id: int,
    obj_in: CertificateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: None = Depends(require_permissions(["ops:write"]))
):
    """Update certificate."""
    certificate = await crud_certificate.get(db, id=cert_id)
    if not certificate:
        raise NotFoundError(detail=f"Certificate with ID {cert_id} not found")

    certificate = await crud_certificate.update(db, db_obj=certificate, obj_in=obj_in)
    return certificate


@router.delete("/certificates/{cert_id}", status_code=status.HTTP_204_NO_CONTENT)
@audit_log(operation_type="DELETE", module="ops", object_type="Certificate")
async def delete_certificate(
    request: Request,
    cert_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: None = Depends(require_permissions(["ops:delete"]))
):
    """Delete certificate."""
    certificate = await crud_certificate.get(db, id=cert_id)
    if not certificate:
        raise NotFoundError(detail=f"Certificate with ID {cert_id} not found")

    await crud_certificate.delete(db, id=cert_id)
    return None


@router.post("/certificates/sync", response_model=CertificateSyncResponse)
@audit_log(operation_type="SYNC", module="ops", object_type="Certificate")
async def sync_certificates_from_prometheus(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: None = Depends(require_permissions(["ops:write"]))
):
    """Sync SSL certificates from Prometheus monitoring."""
    prometheus_client = get_prometheus_client()
    prom_certs = await prometheus_client.get_ssl_certificates()

    created_count = 0
    updated_count = 0
    synced_certs = []

    for prom_cert in prom_certs:
        domain = prom_cert.get("domain", "")
        if not domain:
            continue

        expiry_date_str = prom_cert.get("expiry_date")
        if not expiry_date_str:
            continue

        try:
            expiry_date = datetime.fromisoformat(expiry_date_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            continue

        days_until_expiry = prom_cert.get("days_until_expiry", 0)
        status_str = prom_cert.get("status", "active")

        if status_str == "expired":
            cert_status = "expired"
        elif status_str in ["expiring", "critical"]:
            cert_status = "expiring"
        else:
            cert_status = "active"

        existing_query = select(Certificate).where(Certificate.domain == domain)
        existing_result = await db.execute(existing_query)
        existing_cert = existing_result.scalar_one_or_none()

        if existing_cert:
            existing_cert.valid_until = expiry_date
            existing_cert.days_until_expiry = max(0, days_until_expiry)
            existing_cert.status = cert_status
            existing_cert.issuer = prom_cert.get("job", "unknown")
            existing_cert.subject = domain
            existing_cert.serial_number = f"prom-{domain}"
            updated_count += 1
            synced_certs.append(existing_cert)
        else:
            new_cert = Certificate(
                domain=domain,
                issuer=prom_cert.get("job", "unknown"),
                subject=domain,
                serial_number=f"prom-{domain}",
                valid_from=datetime.utcnow(),
                valid_until=expiry_date,
                days_until_expiry=max(0, days_until_expiry),
                alert_threshold_days=30,
                is_auto_renewal=False,
                status=cert_status,
                asset_ids=[],
            )
            db.add(new_cert)
            created_count += 1
            synced_certs.append(new_cert)

    await db.commit()

    for cert in synced_certs:
        await db.refresh(cert)

    return {
        "total": len(prom_certs),
        "created": created_count,
        "updated": updated_count,
        "certificates": synced_certs,
    }


@router.get("/dns", response_model=list[DNSRecordResponse])
async def list_dns_records(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    domain: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: None = Depends(require_permissions(["ops:read"]))
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
@audit_log(operation_type="CREATE", module="ops", object_type="DNSRecord")
async def create_dns_record(
    request: Request,
    obj_in: DNSRecordCreate,
    db: AsyncSession = Depends(get_db),
    current_user: None = Depends(require_permissions(["ops:write"]))
):
    """Create a new DNS record."""
    record = await crud_dns.create(db, obj_in=obj_in)
    return record


@router.get("/dns/{record_id}", response_model=DNSRecordResponse)
async def get_dns_record(
    record_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: None = Depends(require_permissions(["ops:read"]))
):
    """Get DNS record by ID."""
    record = await crud_dns.get(db, id=record_id)
    if not record:
        raise NotFoundError(detail=f"DNS record with ID {record_id} not found")
    return record


@router.put("/dns/{record_id}", response_model=DNSRecordResponse)
@audit_log(operation_type="UPDATE", module="ops", object_type="DNSRecord")
async def update_dns_record(
    request: Request,
    record_id: int,
    obj_in: DNSRecordUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: None = Depends(require_permissions(["ops:write"]))
):
    """Update DNS record."""
    record = await crud_dns.get(db, id=record_id)
    if not record:
        raise NotFoundError(detail=f"DNS record with ID {record_id} not found")

    record = await crud_dns.update(db, db_obj=record, obj_in=obj_in)
    return record


@router.delete("/dns/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
@audit_log(operation_type="DELETE", module="ops", object_type="DNSRecord")
async def delete_dns_record(
    request: Request,
    record_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: None = Depends(require_permissions(["ops:delete"]))
):
    """Delete DNS record."""
    record = await crud_dns.get(db, id=record_id)
    if not record:
        raise NotFoundError(detail=f"DNS record with ID {record_id} not found")

    await crud_dns.delete(db, id=record_id)
    return None
