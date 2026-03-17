"""
Celery application configuration.
"""
from celery import Celery
from celery.schedules import crontab

from app.config import settings

# Create Celery app
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
    ]
)

# Celery configuration
celery_app.conf.update(
    # Task serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    
    # Timezone
    timezone="UTC",
    enable_utc=True,
    
    # Task settings
    task_track_started=True,
    task_time_limit=3600,  # 1 hour
    task_soft_time_limit=3000,  # 50 minutes
    
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    
    # Result settings
    result_expires=3600 * 24,  # 24 hours
    result_backend=settings.celery_result_backend,
    
    # Beat schedule (will be populated dynamically)
    beat_schedule={},
)


def setup_periodic_tasks(sender, **kwargs):
    """Setup periodic tasks."""
    # Import here to avoid circular imports
    from app.tasks.monitor_tasks import check_all_monitors
    from app.tasks.audit_log_cleanup import cleanup_audit_logs_db, cleanup_audit_logs_file
    from app.tasks.asset_sync_tasks import sync_assets_from_prometheus_task, get_sync_interval

    # Add periodic task for checking monitors every minute
    sender.add_periodic_task(
        60.0,  # Every 60 seconds
        check_all_monitors.s(),
        name="check-all-monitors"
    )

    # Add periodic task for audit log database cleanup - daily at 03:00 UTC
    sender.add_periodic_task(
        crontab(hour=3, minute=0),
        cleanup_audit_logs_db.s(),
        name="cleanup-audit-logs-db"
    )

    # Add periodic task for audit log file cleanup - daily at 03:30 UTC
    sender.add_periodic_task(
        crontab(hour=3, minute=30),
        cleanup_audit_logs_file.s(),
        name="cleanup-audit-logs-file"
    )

    # Add periodic task for asset sync from Prometheus (default: every 30 minutes)
    sync_interval = get_sync_interval()
    sender.add_periodic_task(
        sync_interval,
        sync_assets_from_prometheus_task.s(),
        name="sync-assets-from-prometheus"
    )


@celery_app.on_after_configure.connect
def configure_tasks(sender, **kwargs):
    """Configure tasks after Celery is initialized."""
    setup_periodic_tasks(sender, **kwargs)
