"""
Celery application configuration.
"""
from celery import Celery

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
    
    # Add periodic task for checking monitors every minute
    sender.add_periodic_task(
        60.0,  # Every 60 seconds
        check_all_monitors.s(),
        name="check-all-monitors"
    )


@celery_app.on_after_configure.connect
def configure_tasks(sender, **kwargs):
    """Configure tasks after Celery is initialized."""
    setup_periodic_tasks(sender, **kwargs)
