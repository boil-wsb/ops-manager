from celery import Celery

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
        "app.tasks.feishu_sync_tasks",
        "app.tasks.sync_terminal_metrics",
        "app.tasks.ansible_tasks",
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
