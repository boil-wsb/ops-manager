"""
Inspection task execution.
"""
import asyncio
import subprocess
from datetime import datetime
from celery import shared_task
from sqlalchemy import select

from app.core.logging import get_logger
from app.tasks.utils import get_celery_async_session

logger = get_logger(__name__)


@shared_task(bind=True, max_retries=3)
def run_inspection_task(self, task_id: int):
    """Run an inspection task."""
    
    async def _run():
        from app.models.ops import InspectionTask, InspectionReport
        
        SessionLocal = get_celery_async_session()
        
        async with SessionLocal() as db:
            result = await db.execute(
                select(InspectionTask).where(InspectionTask.id == task_id)
            )
            task = result.scalar_one_or_none()
            
            if not task or not task.is_enabled:
                logger.warning(f"Inspection task {task_id} not found or disabled")
                return
            
            report = InspectionReport(
                task_id=task.id,
                status="running",
                total_checks=len(task.check_items),
                passed_checks=0,
                failed_checks=0,
                warning_checks=0,
                details=[]
            )
            db.add(report)
            await db.commit()
            await db.refresh(report)
            
            task.last_run_at = datetime.utcnow()
            await db.commit()
            
            for check_item in task.check_items:
                check_name = check_item.get("name", "Unknown check")
                command = check_item.get("command", "")
                expected_result = check_item.get("expected_result")
                timeout = check_item.get("timeout", 60)
                
                try:
                    result = subprocess.run(
                        command,
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=timeout
                    )
                    
                    if result.returncode == 0:
                        if expected_result and expected_result not in result.stdout:
                            status = "warning"
                            report.warning_checks += 1
                        else:
                            status = "passed"
                            report.passed_checks += 1
                    else:
                        status = "failed"
                        report.failed_checks += 1
                    
                    report.details.append({
                        "check_name": check_name,
                        "status": status,
                        "message": result.stdout if result.returncode == 0 else result.stderr,
                        "duration_ms": None
                    })
                    
                except subprocess.TimeoutExpired:
                    report.failed_checks += 1
                    report.details.append({
                        "check_name": check_name,
                        "status": "failed",
                        "message": "Check timed out",
                        "duration_ms": timeout * 1000
                    })
                except Exception as e:
                    report.failed_checks += 1
                    report.details.append({
                        "check_name": check_name,
                        "status": "failed",
                        "message": str(e),
                        "duration_ms": None
                    })
            
            report.status = "completed"
            report.summary = f"Passed: {report.passed_checks}, Failed: {report.failed_checks}, Warnings: {report.warning_checks}"
            await db.commit()
            
            logger.info(
                f"Inspection task completed: id={task_id}, name={task.name}, passed={report.passed_checks}, failed={report.failed_checks}"
            )
    
    try:
        asyncio.run(_run())
    except Exception as exc:
        logger.error(f"Inspection task failed: id={task_id}, error={str(exc)}")
        raise self.retry(exc=exc, countdown=60)
