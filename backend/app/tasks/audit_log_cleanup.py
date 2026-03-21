"""
Audit log cleanup tasks for database and file retention.
"""
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from celery import shared_task
from sqlalchemy import delete, func, select

from app.core.logging import get_logger
from app.models.audit_log import AuditLog
from app.tasks.utils import get_celery_async_session

logger = get_logger(__name__)


@shared_task(bind=True, max_retries=3)
def cleanup_audit_logs_db(self) -> dict[str, Any]:
    """Clean up expired audit log records from database.

    Deletes records older than AUDIT_LOG_DB_RETENTION_DAYS.
    """
    from app.config import settings

    start_time = datetime.utcnow()

    async def _cleanup():
        retention_days = settings.audit_log_db_retention_days
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

        logger.info(
            f"Starting audit log database cleanup: retention_days={retention_days}, cutoff={cutoff_date.isoformat()}"
        )

        session_local = get_celery_async_session()

        async with session_local() as db:
            try:
                count_stmt = select(func.count(AuditLog.id)).where(
                    AuditLog.operation_time < cutoff_date
                )
                result = await db.execute(count_stmt)
                records_to_delete = result.scalar() or 0

                if records_to_delete == 0:
                    logger.info("No expired audit log records found in database")
                    return {
                        "deleted_count": 0,
                        "retention_days": retention_days,
                        "cutoff_date": cutoff_date.isoformat(),
                        "message": "No expired records found",
                    }

                delete_stmt = delete(AuditLog).where(
                    AuditLog.operation_time < cutoff_date
                )
                await db.execute(delete_stmt)
                await db.commit()

                execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000

                logger.info(
                    f"Audit log database cleanup completed: deleted={records_to_delete}, time={execution_time:.2f}ms"
                )

                return {
                    "deleted_count": records_to_delete,
                    "retention_days": retention_days,
                    "cutoff_date": cutoff_date.isoformat(),
                    "execution_time_ms": round(execution_time, 2),
                }

            except Exception as e:
                await db.rollback()
                logger.error(f"Audit log database cleanup failed: {str(e)}")
                raise

    try:
        return asyncio.run(_cleanup())
    except Exception as exc:
        logger.error(f"Database cleanup task failed: {str(exc)}")
        countdown = 300 * (5**self.request.retries)
        raise self.retry(exc=exc, countdown=countdown) from exc


@shared_task(bind=True, max_retries=3)
def cleanup_audit_logs_file(self) -> dict[str, Any]:
    """Clean up expired audit log files.

    Deletes .log files in AUDIT_LOG_FILE_PATH directory older than AUDIT_LOG_FILE_RETENTION_DAYS.
    """
    from app.config import settings

    start_time = datetime.utcnow()

    retention_days = settings.audit_log_file_retention_days
    cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

    logger.info(
        f"Starting audit log file cleanup: retention_days={retention_days}, cutoff={cutoff_date.isoformat()}"
    )

    try:
        log_dir = Path(settings.audit_log_file_path).parent

        if not log_dir.exists():
            logger.warning(f"Audit log directory does not exist: {log_dir}")
            return {
                "deleted_count": 0,
                "deleted_files": [],
                "retention_days": retention_days,
                "cutoff_date": cutoff_date.isoformat(),
                "message": f"Directory not found: {log_dir}",
            }

        deleted_files = []

        for log_file in log_dir.glob("*.log*"):
            try:
                stat = log_file.stat()
                mtime = datetime.fromtimestamp(stat.st_mtime)

                if mtime < cutoff_date:
                    file_name = log_file.name
                    log_file.unlink()
                    deleted_files.append(file_name)
                    logger.debug(f"Deleted expired audit log file: {file_name}")
            except OSError as e:
                logger.warning(f"Failed to delete audit log file {log_file}: {str(e)}")

        execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000

        logger.info(
            f"Audit log file cleanup completed: deleted={len(deleted_files)}, time={execution_time:.2f}ms"
        )

        return {
            "deleted_count": len(deleted_files),
            "deleted_files": deleted_files,
            "retention_days": retention_days,
            "cutoff_date": cutoff_date.isoformat(),
            "execution_time_ms": round(execution_time, 2),
        }

    except Exception as exc:
        logger.error(f"File cleanup task failed: {str(exc)}")
        countdown = 300 * (5**self.request.retries)
        raise self.retry(exc=exc, countdown=countdown) from exc


@shared_task(bind=True, max_retries=3)
def cleanup_all_audit_logs(self) -> dict[str, Any]:
    """Run both database and file cleanup tasks."""
    start_time = datetime.utcnow()

    logger.info("Starting complete audit log cleanup (database + files)")

    try:
        db_result = cleanup_audit_logs_db()
        file_result = cleanup_audit_logs_file()

        execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000

        total_records = db_result.get("deleted_count", 0)
        total_files = file_result.get("deleted_count", 0)

        logger.info(
            f"Complete audit log cleanup finished: records={total_records}, files={total_files}, time={execution_time:.2f}ms"
        )

        return {
            "db_cleanup": db_result,
            "file_cleanup": file_result,
            "total_deleted_records": total_records,
            "total_deleted_files": total_files,
            "execution_time_ms": round(execution_time, 2),
        }

    except Exception as exc:
        logger.error(f"Complete audit log cleanup failed: {str(exc)}")
        countdown = 300 * (5**self.request.retries)
        raise self.retry(exc=exc, countdown=countdown) from exc
