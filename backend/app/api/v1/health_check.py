from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_permissions
from app.core.audit import audit_log
from app.core.logging import get_logger
from app.models.user import User
from app.services.health_check_service import health_check_service

logger = get_logger(__name__)

router = APIRouter(prefix="/health-check", tags=["每日健康巡检"])


def _serialize_report(report, silenced_instances: set[str] | None = None) -> dict:
    """Convert ORM model to dict for API response.

    Args:
        report: ORM 报告对象
        silenced_instances: 当前被抑制的主机 instance 集合；若提供，则在每个
            detail 中附加 is_silenced 字段，前端据此展示抑制状态。
    """
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
        data["details"] = [
            _serialize_detail(d, silenced_instances) for d in report.details
        ]
    return data


def _serialize_detail(detail, silenced_instances: set[str] | None = None) -> dict:
    if not detail:
        return None
    is_silenced = False
    if silenced_instances is not None and detail.instance in silenced_instances:
        is_silenced = True
    return {
        "id": detail.id,
        "instance": detail.instance,
        "asset_type": detail.asset_type,
        "host_status": detail.host_status,
        "env": detail.env,
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
        "is_silenced": is_silenced,
    }


def _serialize_silence(silence) -> dict:
    """序列化 AlertSilence 为前端需要的结构。"""
    labels = silence.match_labels or {}
    return {
        "id": silence.id,
        "name": silence.name,
        "instance": labels.get("instance", ""),
        "reason": "",
        "starts_at": silence.starts_at.isoformat() if silence.starts_at else None,
        "ends_at": silence.ends_at.isoformat() if silence.ends_at else None,
        "is_active": silence.is_active,
        "created_by": silence.created_by,
        "created_at": silence.created_at.isoformat() if silence.created_at else None,
        "updated_at": silence.updated_at.isoformat() if silence.updated_at else None,
    }


class SilenceCreateRequest(BaseModel):
    """创建抑制规则请求。"""

    instance: str = Field(..., min_length=1, max_length=255, description="主机 IP/实例")
    reason: str = Field("", max_length=200, description="抑制原因")
    duration_hours: int | None = Field(
        None,
        ge=0,
        description="持续小时数；不传或 0 表示永久抑制",
    )


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
        logger.error(
            f"Health check run error: {e}", extra={"action": "health_check.run", "error": str(e)}
        )
        return {"status": "error", "message": str(e)}


@router.get("/latest")
async def get_latest_report():
    report = await health_check_service.get_latest_report()
    silenced = await health_check_service.get_silenced_instances()
    return _serialize_report(report, silenced)


@router.get("/history")
async def get_report_history(
    days: int = Query(30, description="查询天数"),
    page: int = Query(1, description="页码"),
    page_size: int = Query(20, description="每页数量"),
):
    try:
        result = await health_check_service.get_report_history(days, page, page_size)
        silenced = await health_check_service.get_silenced_instances()
        return {
            "items": [_serialize_report(r, silenced) for r in result["items"]],
            "total": result["total"],
            "page": result["page"],
            "page_size": result["page_size"],
        }
    except Exception as e:
        logger.error(
            f"获取巡检历史失败: {e}", extra={"action": "health_check.history", "error": str(e)}
        )
        raise HTTPException(status_code=500, detail="获取巡检历史记录失败，请稍后重试") from None


@router.get("/reports/{report_id}")
async def get_report_by_id(report_id: int):
    report = await health_check_service.get_report_by_id(report_id)
    silenced = await health_check_service.get_silenced_instances()
    return _serialize_report(report, silenced)


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


# ===== 抑制规则 API =====


@router.get("/silences")
async def list_silences(
    only_active: bool = Query(False, description="仅返回当前生效的抑制规则"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["health-check:read"])),
):
    """获取健康巡检抑制规则列表。"""
    silences = await health_check_service.get_silences(only_active=only_active)
    return [_serialize_silence(s) for s in silences]


@router.post("/silences")
@audit_log(operation_type="CREATE", module="health_check", object_type="HealthCheckSilence")
async def create_silence(
    request: Request,
    payload: SilenceCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["health-check:write"])),
):
    """为指定主机创建抑制规则。

    - duration_hours 为 0 或不传表示永久抑制
    - 抑制规则复用 alert_silences 表，通过 match_labels.source=health_check 标记来源
    """
    try:
        silence = await health_check_service.create_silence(
            instance=payload.instance,
            reason=payload.reason,
            duration_hours=payload.duration_hours,
            created_by=current_user.id if current_user else None,
        )
        return _serialize_silence(silence)
    except Exception as e:
        logger.error(
            f"创建抑制规则失败: {e}",
            extra={
                "action": "health_check.silence.create",
                "instance": payload.instance,
                "error": str(e),
            },
        )
        raise HTTPException(status_code=500, detail=f"创建抑制规则失败: {e}") from None


@router.delete("/silences/{silence_id}")
@audit_log(operation_type="DELETE", module="health_check", object_type="HealthCheckSilence")
async def delete_silence(
    request: Request,
    silence_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["health-check:write"])),
):
    """删除指定的抑制规则。"""
    deleted = await health_check_service.delete_silence(silence_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"抑制规则 {silence_id} 不存在或无权删除")
    return {"message": "已取消抑制", "silence_id": silence_id}
