"""
Audit log CRUD operations.
"""

from datetime import datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.audit_log import AuditLog
from app.schemas.audit_log import AuditLogCreate, AuditLogResponse


class CRUDAuditLog(CRUDBase[AuditLog, AuditLogCreate, AuditLogResponse]):
    """Audit log CRUD operations."""

    async def get_multi_with_filters(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 20,
        operator_id: int | None = None,
        operation_type: str | None = None,
        operation_module: str | None = None,
        object_type: str | None = None,
        status: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        keyword: str | None = None,
    ) -> tuple[list[AuditLog], int]:
        """Get audit logs with filters and pagination.

        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            operator_id: Filter by operator ID
            operation_type: Filter by operation type
            operation_module: Filter by operation module
            object_type: Filter by object type
            status: Filter by operation status
            start_time: Filter by start time (inclusive)
            end_time: Filter by end time (inclusive)
            keyword: Search keyword for object_name and operator_name

        Returns:
            Tuple of (list of audit logs, total count)
        """
        # Build base query
        query = select(AuditLog)

        # Apply filters
        filters = []

        if operator_id is not None:
            filters.append(AuditLog.operator_id == operator_id)

        if operation_type:
            filters.append(AuditLog.operation_type == operation_type)

        if operation_module:
            filters.append(AuditLog.operation_module == operation_module)

        if object_type:
            filters.append(AuditLog.object_type == object_type)

        if status:
            filters.append(AuditLog.status == status)

        if start_time:
            filters.append(AuditLog.operation_time >= start_time)

        if end_time:
            filters.append(AuditLog.operation_time <= end_time)

        if keyword:
            filters.append(
                or_(
                    AuditLog.object_name.ilike(f"%{keyword}%"),
                    AuditLog.operator_name.ilike(f"%{keyword}%"),
                )
            )

        if filters:
            query = query.where(and_(*filters))

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Apply sorting (default by operation_time desc)
        query = query.order_by(AuditLog.operation_time.desc())

        # Apply pagination
        query = query.offset(skip).limit(limit)

        # Execute query
        result = await db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def get_by_id(self, db: AsyncSession, *, log_id: int) -> AuditLog | None:
        """Get audit log by ID.

        Args:
            db: Database session
            log_id: Audit log ID

        Returns:
            Audit log or None
        """
        result = await db.execute(select(AuditLog).where(AuditLog.id == log_id))
        return result.scalar_one_or_none()


crud_audit_log = CRUDAuditLog(AuditLog)
