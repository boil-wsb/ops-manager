"""
Alert CRUD operations.
"""

from datetime import datetime

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.alert import AlertHistory, AlertSilence, AlertTemplate
from app.schemas.alert import (
    AlertSilenceCreate,
    AlertSilenceUpdate,
    AlertTemplateCreate,
    AlertTemplateUpdate,
)


class CRUDAlertSilence(CRUDBase[AlertSilence, AlertSilenceCreate, AlertSilenceUpdate]):
    """Alert silence CRUD operations."""

    async def get_active_silences(
        self, db: AsyncSession, current_time: datetime | None = None
    ) -> list[AlertSilence]:
        """Get all active and currently effective silences."""
        if current_time is None:
            current_time = datetime.utcnow()

        result = await db.execute(
            select(AlertSilence).where(
                and_(
                    AlertSilence.is_active,
                    AlertSilence.starts_at <= current_time,
                    AlertSilence.ends_at >= current_time,
                )
            )
        )
        return list(result.scalars().all())

    async def get_by_match_labels(
        self,
        db: AsyncSession,
        labels: dict,
    ) -> list[AlertSilence]:
        """Get silences that match the given labels."""
        silences = await self.get_active_silences(db)
        matched = []
        for silence in silences:
            if all(
                silence.match_labels.get(k) == v
                for k, v in labels.items()
                if k in silence.match_labels
            ):
                matched.append(silence)
        return matched


class CRUDAlertTemplate(CRUDBase[AlertTemplate, AlertTemplateCreate, AlertTemplateUpdate]):
    """Alert template CRUD operations."""

    async def get_default_template(
        self, db: AsyncSession, template_type: str
    ) -> AlertTemplate | None:
        """Get the default template for a given type."""
        result = await db.execute(
            select(AlertTemplate).where(
                and_(
                    AlertTemplate.template_type == template_type,
                    AlertTemplate.is_default,
                    AlertTemplate.is_active,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_active_templates(
        self, db: AsyncSession, template_type: str | None = None
    ) -> list[AlertTemplate]:
        """Get all active templates, optionally filtered by type."""
        query = select(AlertTemplate).where(AlertTemplate.is_active)
        if template_type:
            query = query.where(AlertTemplate.template_type == template_type)

        result = await db.execute(query)
        return list(result.scalars().all())


class CRUDAlertHistory(CRUDBase):
    """Alert history CRUD operations (read-only, no create/update/delete base methods needed)."""

    async def get_multi_with_filters(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 20,
        alertname: str | None = None,
        status: str | None = None,
        severity: str | None = None,
        is_suppressed: bool | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> tuple[list[AlertHistory], int]:
        """Get alert history with filters and pagination."""
        query = select(AlertHistory)

        if alertname:
            query = query.where(AlertHistory.alertname == alertname)
        if status:
            query = query.where(AlertHistory.status == status)
        if severity:
            query = query.where(AlertHistory.severity == severity)
        if is_suppressed is not None:
            query = query.where(AlertHistory.is_suppressed == is_suppressed)
        if start_time:
            query = query.where(AlertHistory.starts_at >= start_time)
        if end_time:
            query = query.where(AlertHistory.ends_at <= end_time)

        from sqlalchemy import func

        count_result = await db.execute(select(func.count()).select_from(AlertHistory))
        total = count_result.scalar() or 0

        query = query.offset(skip).limit(limit).order_by(AlertHistory.created_at.desc())

        result = await db.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def create_from_alertmanager(
        self,
        db: AsyncSession,
        *,
        alertname: str,
        status: str,
        severity: str,
        labels: dict,
        annotations: dict,
        starts_at: datetime,
        ends_at: datetime | None = None,
        is_suppressed: bool = False,
        silence_id: int | None = None,
    ) -> AlertHistory:
        """Create alert history from Alertmanager webhook payload."""
        db_obj = AlertHistory(
            alertname=alertname,
            status=status,
            severity=severity,
            labels=labels,
            annotations=annotations,
            starts_at=starts_at,
            ends_at=ends_at,
            is_suppressed=is_suppressed,
            silence_id=silence_id,
            notification_sent=False,
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj


crud_alert_silence = CRUDAlertSilence(AlertSilence)
crud_alert_template = CRUDAlertTemplate(AlertTemplate)
crud_alert_history = CRUDAlertHistory(AlertHistory)
