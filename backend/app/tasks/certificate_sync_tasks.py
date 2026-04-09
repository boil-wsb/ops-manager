"""
证书同步定时任务

从 Prometheus 自动同步 SSL 证书数据
"""

import asyncio
import logging
from datetime import datetime
from typing import Any

from celery import shared_task

from app.config import settings
from app.services.prometheus import PrometheusClient
from app.tasks.utils import get_celery_async_session

logger = logging.getLogger(__name__)


@shared_task(
    name="tasks.sync_certificates_from_prometheus",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def sync_certificates_from_prometheus_task(self) -> dict[str, Any]:
    """从 Prometheus 同步 SSL 证书的 Celery 任务

    每日执行一次，自动同步所有监控的 SSL 证书信息
    """
    if not getattr(settings, "PROMETHEUS_SYNC_ENABLED", True):
        logger.info("Certificate sync from Prometheus is disabled")
        return {"status": "skipped", "reason": "sync_disabled"}

    logger.info("Starting scheduled certificate sync from Prometheus")
    start_time = datetime.utcnow()

    async def _sync():
        session_local = get_celery_async_session()

        async with session_local() as db:
            try:
                from sqlalchemy import select

                from app.models.ops import Certificate

                prometheus_client = PrometheusClient()
                prom_certs = await prometheus_client.get_ssl_certificates()

                created_count = 0
                updated_count = 0

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

                await db.commit()

                end_time = datetime.utcnow()
                duration = (end_time - start_time).total_seconds()

                task_result = {
                    "status": "success",
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "duration_seconds": duration,
                    "total": len(prom_certs),
                    "created": created_count,
                    "updated": updated_count,
                }

                logger.info(f"Certificate sync completed: {task_result}")
                return task_result

            except Exception as exc:
                logger.error(f"Certificate sync failed: {exc}")
                raise self.retry(exc=exc) from exc

    return asyncio.run(_sync())
