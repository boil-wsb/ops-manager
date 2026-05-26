"""
证书同步定时任务

从 Prometheus 自动同步 SSL 证书数据
"""

from app.core.logging import get_logger
from datetime import datetime
from typing import Any

from app.config import settings
from app.db.session import db_operation_with_retry
from app.core.tz import now_shanghai
from app.services.prometheus import PrometheusClient

logger = get_logger(__name__)


async def _sync_certificates_db(db) -> dict[str, Any]:
    from sqlalchemy import select

    from app.models.ops import Certificate

    start_time = now_shanghai()

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
                valid_from=now_shanghai(),
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

    end_time = now_shanghai()
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

    logger.info("证书同步完成", extra={"action": "cert.sync", "result": task_result})
    return task_result


async def sync_certificates_from_prometheus_task() -> dict[str, Any]:
    """从 Prometheus 同步 SSL 证书的定时任务

    每日执行一次，自动同步所有监控的 SSL 证书信息
    """
    if not getattr(settings, "PROMETHEUS_SYNC_ENABLED", True):
        logger.info("证书同步已禁用", extra={"action": "cert.sync"})
        return {"status": "skipped", "reason": "sync_disabled"}

    logger.info("开始定时证书同步", extra={"action": "cert.sync"})

    try:
        return await db_operation_with_retry(
            _sync_certificates_db, max_retries=3, retry_delay=2.0
        )
    except Exception as exc:
        logger.error(f"证书同步失败: {exc}", extra={"action": "cert.sync"})
        raise
