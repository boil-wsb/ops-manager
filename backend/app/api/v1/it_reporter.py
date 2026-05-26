from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.exceptions import PermissionDeniedError
from app.core.logging import get_logger
from app.crud.crud_scheduled_task import crud_scheduled_task
from app.integrations.minio.client import generate_presigned_url
from app.schemas.it_reporter import ITReporterRequest, ITReporterResponse
from app.services.it_reporter_service import it_reporter_service

logger = get_logger(__name__)

router = APIRouter(prefix="/it-reporter", tags=["IT巡检报告"])


@router.post("", response_model=ITReporterResponse)
async def process_it_report(
    request: ITReporterRequest,
    db: AsyncSession = Depends(get_db),
):
    task = await crud_scheduled_task.get_by_task_id(db, "process-it-report")
    if not task or not task.is_enabled:
        raise PermissionDeniedError(detail="IT巡检报告处理任务已禁用，无法执行")

    chat_id = request.chat_id
    if not chat_id:
        chat_id = await it_reporter_service.get_chat_id_from_config()

    try:
        result = await it_reporter_service.process_report(
            report_path=request.report_path,
            minio_bucket=request.minio_bucket,
            chat_id=chat_id,
        )
        return ITReporterResponse(**result)
    except Exception as e:
        logger.error(f"IT reporter error: {e}", extra={"action": "it_reporter.run", "error": str(e)})
        return ITReporterResponse(
            status="error",
            message=str(e),
        )


@router.get("/download")
async def download_report(
    bucket: str = Query(..., description="MinIO 存储桶名称"),
    path: str = Query(..., description="MinIO 对象路径"),
    expires_hours: int = Query(168, description="预签名 URL 有效期（小时）"),
):
    presigned_url = generate_presigned_url(bucket, path, expires_hours=expires_hours)
    if not presigned_url:
        return RedirectResponse(
            url=f"/api/v1/it-reporter/download-error?bucket={bucket}&path={path}",
            status_code=302,
        )
    return RedirectResponse(url=presigned_url, status_code=302)
