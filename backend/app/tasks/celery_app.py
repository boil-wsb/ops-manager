"""
Celery application configuration.
"""
from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery_app = Celery(
    "opsmanager",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.tasks.monitor_tasks",
        "app.tasks.inspection_tasks",
        "app.tasks.notification_tasks",
        "app.tasks.audit_log_cleanup",
        "app.tasks.asset_sync_tasks",
        "app.tasks.certificate_sync_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=False,
    task_track_started=True,
    task_time_limit=3600,
    task_soft_time_limit=3000,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    result_expires=3600 * 24,
    result_backend=settings.celery_result_backend,
    beat_schedule={},
)


def setup_periodic_tasks(sender, **kwargs):
    """Setup periodic tasks."""
    from app.tasks.asset_sync_tasks import get_sync_interval, sync_assets_from_prometheus_task
    from app.tasks.audit_log_cleanup import cleanup_audit_logs_db, cleanup_audit_logs_file
    from app.tasks.certificate_sync_tasks import sync_certificates_from_prometheus_task
    from app.tasks.monitor_tasks import check_all_monitors

    sender.add_periodic_task(
        60.0,
        check_all_monitors.s(),
        name="check-all-monitors",
    )

    sender.add_periodic_task(
        crontab(hour=3, minute=0),
        cleanup_audit_logs_db.s(),
        name="cleanup-audit-logs-db",
    )

    sender.add_periodic_task(
        crontab(hour=3, minute=30),
        cleanup_audit_logs_file.s(),
        name="cleanup-audit-logs-file",
    )

    sync_interval = get_sync_interval()
    sender.add_periodic_task(
        sync_interval,
        sync_assets_from_prometheus_task.s(),
        name="sync-assets-from-prometheus",
    )

    sender.add_periodic_task(
        crontab(hour=3, minute=0),
        sync_certificates_from_prometheus_task.s(),
        name="sync-certificates-from-prometheus",
    )


@celery_app.on_after_configure.connect
def configure_tasks(sender, **kwargs):
    """Configure tasks after Celery is initialized."""
    setup_periodic_tasks(sender, **kwargs)
