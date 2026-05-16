from fastapi import APIRouter

from app.core.logging import get_logger
from app.schemas.it_reporter import ITReporterRequest, ITReporterResponse
from app.services.it_reporter_service import it_reporter_service

logger = get_logger(__name__)

router = APIRouter(prefix="/it-reporter", tags=["IT巡检报告"])


@router.post("", response_model=ITReporterResponse)
async def process_it_report(
    request: ITReporterRequest,
):
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
        logger.error(f"IT reporter error: {e}")
        return ITReporterResponse(
            status="error",
            message=str(e),
        )
