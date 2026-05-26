from app.core.logging import get_logger
from app.services.health_check_service import health_check_service

logger = get_logger(__name__)


async def daily_health_check_task():
    """Daily health check task - triggered by scheduler"""
    try:
        report = await health_check_service.generate_health_report()
        return {
            "status": "success",
            "result_summary": f"巡检完成: 共{report.total_hosts}台主机, 正常{report.ok_count}, 警告{report.warning_count}, 严重{report.critical_count}",
        }
    except Exception as e:
        logger.error(f"每日健康检查任务失败: {e}", extra={"action": "health_check.run"})
        return {"status": "failed", "error": str(e)}
