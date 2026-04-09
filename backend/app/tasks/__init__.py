"""
Celery tasks for background job processing.
"""

from app.tasks.audit_log_cleanup import (
    cleanup_all_audit_logs,
    cleanup_audit_logs_db,
    cleanup_audit_logs_file,
)
from app.tasks.feishu_sync_tasks import sync_feishu_users_task
from app.tasks.inspection_tasks import run_inspection_task
from app.tasks.monitor_tasks import check_all_monitors
from app.tasks.notification_tasks import (
    send_alert_notification,
    send_email_notification,
    send_webhook_notification,
)
from app.tasks.sync_terminal_metrics import sync_terminal_metrics_task

__all__ = [
    # Audit log cleanup
    "cleanup_audit_logs_db",
    "cleanup_audit_logs_file",
    "cleanup_all_audit_logs",
    # Feishu sync
    "sync_feishu_users_task",
    # Inspection tasks
    "run_inspection_task",
    # Monitor tasks
    "check_all_monitors",
    # Notification tasks
    "send_email_notification",
    "send_webhook_notification",
    "send_alert_notification",
    # Terminal metrics sync
    "sync_terminal_metrics_task",
]
