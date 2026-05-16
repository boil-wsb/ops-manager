from datetime import datetime
from zoneinfo import ZoneInfo

from app.core.logging import get_logger
from app.db.session import get_session_maker
from app.services.it_reporter_service import it_reporter_service

logger = get_logger(__name__)


async def process_it_report_task() -> dict:
    try:
        session_maker = get_session_maker()

        chat_id = None
        minio_bucket = None
        report_path = None

        async with session_maker() as db:
            from app.crud.crud_system_config import crud_system_config

            chat_id = await crud_system_config.get_value(db, "itreporter.chat_id")
            minio_bucket = await crud_system_config.get_value(db, "itreporter.minio_bucket")
            report_path = await crud_system_config.get_value(db, "itreporter.report_path")

        if not chat_id:
            logger.warning("IT reporter chat_id not configured in system_configs")
            return {"status": "skipped", "error": "chat_id not configured"}

        if not report_path:
            logger.warning("IT reporter report_path not configured in system_configs")
            return {"status": "skipped", "error": "report_path not configured"}

        if not minio_bucket:
            minio_bucket = "reports"

        today = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d")
        report_path = report_path.replace("{date}", today)

        result = await it_reporter_service.process_report(
            report_path=report_path,
            minio_bucket=minio_bucket,
            chat_id=chat_id,
        )

        presigned_url = None
        if result.get("data"):
            presigned_url = result["data"].get("presigned_url")

        summary_parts = [f"status={result.get('status', 'unknown')}"]
        if presigned_url:
            summary_parts.append(f"presigned_url={presigned_url}")
        feishu_sent = result.get("data", {}).get("feishu_message_sent")
        if feishu_sent is not None:
            summary_parts.append(f"feishu_sent={feishu_sent}")

        return {
            "status": result.get("status", "success"),
            "message": result.get("message", ""),
            "presigned_url": presigned_url,
            "result_summary": ", ".join(summary_parts),
        }

    except Exception as e:
        logger.error(f"IT reporter task error: {e}")
        return {"status": "failed", "error": str(e)}
