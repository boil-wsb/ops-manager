from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse, Response

from app.core.logging import get_logger
from app.services.health_check_service import health_check_service

logger = get_logger(__name__)

router = APIRouter(prefix="/health-check", tags=["每日健康巡检"])


def _serialize_report(report) -> dict:
    """Convert ORM model to dict for API response"""
    if not report:
        return None
    data = {
        "id": report.id,
        "report_time": report.report_time.isoformat() if report.report_time else None,
        "source": report.source,
        "total_hosts": report.total_hosts,
        "ok_count": report.ok_count,
        "warning_count": report.warning_count,
        "critical_count": report.critical_count,
        "notification_sent": report.notification_sent,
        "created_at": report.created_at.isoformat() if report.created_at else None,
    }
    if hasattr(report, "details") and report.details:
        data["details"] = [_serialize_detail(d) for d in report.details]
    return data


def _serialize_detail(detail) -> dict:
    if not detail:
        return None
    return {
        "id": detail.id,
        "instance": detail.instance,
        "asset_type": detail.asset_type,
        "host_status": detail.host_status,
        "os_info": detail.os_info,
        "kernel_version": detail.kernel_version,
        "cpu_count": detail.cpu_count,
        "cpu_usage": detail.cpu_usage,
        "load1": detail.load1,
        "load5": detail.load5,
        "load15": detail.load15,
        "memory_usage": detail.memory_usage,
        "memory_total_mb": detail.memory_total_mb,
        "memory_used_mb": detail.memory_used_mb,
        "disk_usage": detail.disk_usage,
        "disk_total_gb": detail.disk_total_gb,
        "is_online": detail.is_online,
        "check_details": detail.check_details,
        "checked_at": detail.checked_at.isoformat() if detail.checked_at else None,
    }


@router.post("/run")
async def run_health_check():
    try:
        report = await health_check_service.generate_health_report()
        return {
            "status": "success",
            "message": "巡检完成",
            "data": {
                "report_id": report.id,
                "total_hosts": report.total_hosts,
                "ok_count": report.ok_count,
                "warning_count": report.warning_count,
                "critical_count": report.critical_count,
            },
        }
    except Exception as e:
        logger.error(f"Health check run error: {e}", extra={"action": "health_check.run", "error": str(e)})
        return {"status": "error", "message": str(e)}


@router.get("/latest")
async def get_latest_report():
    report = await health_check_service.get_latest_report()
    return _serialize_report(report)


@router.get("/history")
async def get_report_history(
    days: int = Query(30, description="查询天数"),
    page: int = Query(1, description="页码"),
    page_size: int = Query(20, description="每页数量"),
):
    try:
        result = await health_check_service.get_report_history(days, page, page_size)
        return {
            "items": [_serialize_report(r) for r in result["items"]],
            "total": result["total"],
            "page": result["page"],
            "page_size": result["page_size"],
        }
    except Exception as e:
        logger.error(f"获取巡检历史失败: {e}", extra={"action": "health_check.history", "error": str(e)})
        raise HTTPException(status_code=500, detail="获取巡检历史记录失败，请稍后重试")


@router.get("/reports/{report_id}")
async def get_report_by_id(report_id: int):
    report = await health_check_service.get_report_by_id(report_id)
    return _serialize_report(report)


@router.get("/reports/{report_id}/export/html")
async def export_html_report(report_id: int):
    html_content = await health_check_service.export_html_report(report_id)
    return HTMLResponse(content=html_content, media_type="text/html")


@router.get("/reports/{report_id}/export/excel")
async def export_excel_report(report_id: int):
    excel_data = await health_check_service.export_excel_report(report_id)
    return Response(
        content=excel_data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename=health_check_report_{report_id}.xlsx",
        },
    )


@router.get("/thresholds")
async def get_thresholds():
    thresholds = await health_check_service.get_thresholds()
    return thresholds


@router.put("/thresholds")
async def update_thresholds(thresholds: dict):
    result = await health_check_service.update_thresholds(thresholds)
    return result
