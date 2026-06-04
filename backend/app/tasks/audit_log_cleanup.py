"""
Audit log cleanup tasks for database and file retention.
"""

from datetime import timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import delete, func, select

from app.core.logging import get_logger
from app.core.tz import from_timestamp, now_shanghai
from app.db.session import db_operation_with_retry
from app.models.audit_log import AuditLog

logger = get_logger(__name__)


async def _cleanup_audit_logs_db_op(db, cutoff_date) -> int:
    count_stmt = select(func.count(AuditLog.id)).where(AuditLog.operation_time < cutoff_date)
    result = await db.execute(count_stmt)
    records_to_delete = result.scalar() or 0

    if records_to_delete == 0:
        return 0

    delete_stmt = delete(AuditLog).where(AuditLog.operation_time < cutoff_date)
    await db.execute(delete_stmt)
    await db.commit()

    return records_to_delete


async def cleanup_audit_logs_db() -> dict[str, Any]:
    """Clean up expired audit log records from database.

    Deletes records older than AUDIT_LOG_DB_RETENTION_DAYS.
    """
    from app.config import settings

    start_time = now_shanghai()

    retention_days = settings.audit_log_db_retention_days
    cutoff_date = now_shanghai() - timedelta(days=retention_days)

    logger.info(
        "开始审计日志数据库清理",
        extra={
            "action": "audit.cleanup",
            "retention_days": retention_days,
            "cutoff": cutoff_date.isoformat(),
        },
    )

    try:
        records_to_delete = await db_operation_with_retry(
            lambda db: _cleanup_audit_logs_db_op(db, cutoff_date),
            max_retries=3,
            retry_delay=2.0,
        )

        if records_to_delete == 0:
            logger.info("未发现过期审计日志记录", extra={"action": "audit.cleanup"})
            return {
                "deleted_count": 0,
                "retention_days": retention_days,
                "cutoff_date": cutoff_date.isoformat(),
                "message": "No expired records found",
            }

        execution_time = (now_shanghai() - start_time).total_seconds() * 1000

        logger.info(
            "审计日志数据库清理完成",
            extra={
                "action": "audit.cleanup",
                "deleted": records_to_delete,
                "execution_time_ms": round(execution_time, 2),
            },
        )

        return {
            "deleted_count": records_to_delete,
            "retention_days": retention_days,
            "cutoff_date": cutoff_date.isoformat(),
            "execution_time_ms": round(execution_time, 2),
        }

    except Exception as e:
        logger.error(f"审计日志数据库清理失败: {str(e)}", extra={"action": "audit.cleanup"})
        raise


async def cleanup_audit_logs_file() -> dict[str, Any]:
    """Clean up expired audit log files.

    Deletes .log files in AUDIT_LOG_FILE_PATH directory older than AUDIT_LOG_FILE_RETENTION_DAYS.
    """
    from app.config import settings

    start_time = now_shanghai()

    retention_days = settings.audit_log_file_retention_days
    cutoff_date = now_shanghai() - timedelta(days=retention_days)

    logger.info(
        "开始审计日志文件清理",
        extra={
            "action": "audit.cleanup",
            "retention_days": retention_days,
            "cutoff": cutoff_date.isoformat(),
        },
    )

    try:
        log_dir = Path(settings.audit_log_file_path).parent

        if not log_dir.exists():
            logger.warning(f"审计日志目录不存在: {log_dir}", extra={"action": "audit.cleanup"})
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
                mtime = from_timestamp(stat.st_mtime)

                if mtime < cutoff_date:
                    file_name = log_file.name
                    log_file.unlink()
                    deleted_files.append(file_name)
                    logger.debug(
                        f"删除过期审计日志文件: {file_name}", extra={"action": "audit.cleanup"}
                    )
            except OSError as e:
                logger.warning(f"删除审计日志文件失败: {str(e)}", extra={"action": "audit.cleanup"})

        execution_time = (now_shanghai() - start_time).total_seconds() * 1000

        logger.info(
            "审计日志文件清理完成",
            extra={
                "action": "audit.cleanup",
                "deleted": len(deleted_files),
                "execution_time_ms": round(execution_time, 2),
            },
        )

        return {
            "deleted_count": len(deleted_files),
            "deleted_files": deleted_files,
            "retention_days": retention_days,
            "cutoff_date": cutoff_date.isoformat(),
            "execution_time_ms": round(execution_time, 2),
        }

    except Exception as exc:
        logger.error(f"文件清理任务失败: {str(exc)}", extra={"action": "audit.cleanup"})
        raise


async def cleanup_all_audit_logs() -> dict[str, Any]:
    """Run both database and file cleanup tasks."""
    start_time = now_shanghai()

    logger.info("开始完整审计日志清理", extra={"action": "audit.cleanup"})

    try:
        db_result = await cleanup_audit_logs_db()
        file_result = await cleanup_audit_logs_file()

        execution_time = (now_shanghai() - start_time).total_seconds() * 1000

        total_records = db_result.get("deleted_count", 0)
        total_files = file_result.get("deleted_count", 0)

        logger.info(
            "完整审计日志清理完成",
            extra={
                "action": "audit.cleanup",
                "records": total_records,
                "files": total_files,
                "execution_time_ms": round(execution_time, 2),
            },
        )

        return {
            "db_cleanup": db_result,
            "file_cleanup": file_result,
            "total_deleted_records": total_records,
            "total_deleted_files": total_files,
            "execution_time_ms": round(execution_time, 2),
        }

    except Exception as exc:
        logger.error(f"完整审计日志清理失败: {str(exc)}", extra={"action": "audit.cleanup"})
        raise
