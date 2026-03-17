"""
Audit log cleanup tasks for database and file retention.
"""
import os
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any
from celery import shared_task
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.config import settings
from app.db.session import AsyncSessionLocal
from app.models.audit_log import AuditLog

logger = get_logger(__name__)


@shared_task(bind=True, max_retries=3)
def cleanup_audit_logs_db(self) -> Dict[str, Any]:
    """
    Clean up expired audit log records from database.
    
    Deletes records older than AUDIT_LOG_DB_RETENTION_DAYS.
    
    Returns:
        Dict containing cleanup statistics:
        - deleted_count: Number of records deleted
        - retention_days: Retention period used
        - cutoff_date: Date before which records were deleted
        - execution_time_ms: Task execution time in milliseconds
    """
    start_time = datetime.utcnow()
    
    async def _cleanup():
        retention_days = settings.audit_log_db_retention_days
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        
        logger.info(
            "Starting audit log database cleanup",
            retention_days=retention_days,
            cutoff_date=cutoff_date.isoformat()
        )
        
        async with AsyncSessionLocal() as db:
            try:
                # First, count records to be deleted
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
                        "message": "No expired records found"
                    }
                
                # Delete expired records
                delete_stmt = delete(AuditLog).where(
                    AuditLog.operation_time < cutoff_date
                )
                await db.execute(delete_stmt)
                await db.commit()
                
                execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                
                logger.info(
                    "Audit log database cleanup completed",
                    deleted_count=records_to_delete,
                    retention_days=retention_days,
                    cutoff_date=cutoff_date.isoformat(),
                    execution_time_ms=round(execution_time, 2)
                )
                
                return {
                    "deleted_count": records_to_delete,
                    "retention_days": retention_days,
                    "cutoff_date": cutoff_date.isoformat(),
                    "execution_time_ms": round(execution_time, 2)
                }
                
            except Exception as e:
                await db.rollback()
                logger.error(
                    "Audit log database cleanup failed",
                    error=str(e),
                    retention_days=retention_days,
                    cutoff_date=cutoff_date.isoformat()
                )
                raise
    
    try:
        return asyncio.run(_cleanup())
    except Exception as exc:
        logger.error("Database cleanup task failed", error=str(exc), retry_count=self.request.retries)
        # Retry with exponential backoff: 5min, 25min
        countdown = 300 * (5 ** self.request.retries)
        raise self.retry(exc=exc, countdown=countdown)


@shared_task(bind=True, max_retries=3)
def cleanup_audit_logs_file(self) -> Dict[str, Any]:
    """
    Clean up expired audit log files.
    
    Deletes .log files in AUDIT_LOG_FILE_PATH directory older than AUDIT_LOG_FILE_RETENTION_DAYS.
    
    Returns:
        Dict containing cleanup statistics:
        - deleted_count: Number of files deleted
        - deleted_files: List of deleted file names
        - retention_days: Retention period used
        - cutoff_date: Date before which files were deleted
        - execution_time_ms: Task execution time in milliseconds
    """
    start_time = datetime.utcnow()
    
    retention_days = settings.audit_log_file_retention_days
    cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
    
    logger.info(
        "Starting audit log file cleanup",
        retention_days=retention_days,
        cutoff_date=cutoff_date.isoformat(),
        file_path=settings.audit_log_file_path
    )
    
    try:
        # Get the directory from file path
        log_dir = Path(settings.audit_log_file_path).parent
        
        if not log_dir.exists():
            logger.warning(
                "Audit log directory does not exist",
                directory=str(log_dir)
            )
            return {
                "deleted_count": 0,
                "deleted_files": [],
                "retention_days": retention_days,
                "cutoff_date": cutoff_date.isoformat(),
                "message": f"Directory not found: {log_dir}"
            }
        
        deleted_files = []
        
        # Scan for .log files
        for log_file in log_dir.glob("*.log*"):  # Include rotated logs like audit.log.1, audit.log.2.gz
            try:
                # Get file modification time
                stat = log_file.stat()
                mtime = datetime.fromtimestamp(stat.st_mtime)
                
                if mtime < cutoff_date:
                    # File is expired, delete it
                    file_name = log_file.name
                    log_file.unlink()
                    deleted_files.append(file_name)
                    logger.debug(
                        "Deleted expired audit log file",
                        file=file_name,
                        modified_time=mtime.isoformat()
                    )
            except OSError as e:
                logger.warning(
                    "Failed to delete audit log file",
                    file=str(log_file),
                    error=str(e)
                )
        
        execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        logger.info(
            "Audit log file cleanup completed",
            deleted_count=len(deleted_files),
            deleted_files=deleted_files,
            retention_days=retention_days,
            execution_time_ms=round(execution_time, 2)
        )
        
        return {
            "deleted_count": len(deleted_files),
            "deleted_files": deleted_files,
            "retention_days": retention_days,
            "cutoff_date": cutoff_date.isoformat(),
            "execution_time_ms": round(execution_time, 2)
        }
        
    except Exception as exc:
        logger.error("File cleanup task failed", error=str(exc), retry_count=self.request.retries)
        # Retry with exponential backoff: 5min, 25min
        countdown = 300 * (5 ** self.request.retries)
        raise self.retry(exc=exc, countdown=countdown)


@shared_task(bind=True, max_retries=3)
def cleanup_all_audit_logs(self) -> Dict[str, Any]:
    """
    Run both database and file cleanup tasks.
    
    This is a convenience task that runs both cleanup operations sequentially.
    
    Returns:
        Dict containing results from both cleanup operations:
        - db_cleanup: Results from database cleanup
        - file_cleanup: Results from file cleanup
        - total_deleted_records: Total database records deleted
        - total_deleted_files: Total files deleted
        - execution_time_ms: Total execution time in milliseconds
    """
    start_time = datetime.utcnow()
    
    logger.info("Starting complete audit log cleanup (database + files)")
    
    try:
        # Run database cleanup
        db_result = cleanup_audit_logs_db()
        
        # Run file cleanup
        file_result = cleanup_audit_logs_file()
        
        execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        total_records = db_result.get("deleted_count", 0)
        total_files = file_result.get("deleted_count", 0)
        
        logger.info(
            "Complete audit log cleanup finished",
            total_deleted_records=total_records,
            total_deleted_files=total_files,
            execution_time_ms=round(execution_time, 2)
        )
        
        return {
            "db_cleanup": db_result,
            "file_cleanup": file_result,
            "total_deleted_records": total_records,
            "total_deleted_files": total_files,
            "execution_time_ms": round(execution_time, 2)
        }
        
    except Exception as exc:
        logger.error("Complete audit log cleanup failed", error=str(exc), retry_count=self.request.retries)
        # Retry with exponential backoff
        countdown = 300 * (5 ** self.request.retries)
        raise self.retry(exc=exc, countdown=countdown)
