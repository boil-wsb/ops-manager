from datetime import datetime
from zoneinfo import ZoneInfo

from app.config import settings
from app.core.logging import get_logger
from app.db.session import db_operation_with_retry
from app.integrations.minio.client import find_latest_object_by_prefix
from app.services.it_reporter_service import it_reporter_service

logger = get_logger(__name__)


async def _get_it_reporter_config(db) -> dict:
    from app.crud.crud_system_config import crud_system_config

    chat_id = await crud_system_config.get_value(db, "itreporter.chat_id")
    minio_bucket = await crud_system_config.get_value(db, "itreporter.minio_bucket")
    report_path = await crud_system_config.get_value(db, "itreporter.report_path")

    return {
        "chat_id": chat_id,
        "minio_bucket": minio_bucket,
        "report_path": report_path,
    }


async def process_it_report_task() -> dict:
    try:
        config = await db_operation_with_retry(
            _get_it_reporter_config, max_retries=3, retry_delay=2.0
        )

        chat_id = config["chat_id"]
        minio_bucket = config["minio_bucket"]
        report_path = config["report_path"]

        if not chat_id:
            logger.warning("IT报告 chat_id 未配置", extra={"action": "it_reporter.run"})
            return {"status": "skipped", "error": "chat_id not configured"}

        if not report_path:
            logger.warning("IT报告 report_path 未配置", extra={"action": "it_reporter.run"})
            return {"status": "skipped", "error": "report_path not configured"}

        if not minio_bucket:
            minio_bucket = settings.itreporter_minio_bucket

        today = datetime.now(ZoneInfo("Asia/Shanghai"))
        report_path = report_path.replace("{date}", today.strftime("%Y-%m-%d"))
        report_path = report_path.replace("{date_compact}", today.strftime("%Y%m%d"))

        resolved_path = find_latest_object_by_prefix(minio_bucket, report_path)
        if not resolved_path:
            logger.error(f"未找到匹配的报告: {minio_bucket}/{report_path}", extra={"action": "it_reporter.run"})
            return {"status": "failed", "error": f"No report found matching prefix: {report_path}"}

        logger.info("报告路径解析完成", extra={"action": "it_reporter.run", "report_path": report_path, "resolved_path": resolved_path})

        result = await it_reporter_service.process_report(
            report_path=resolved_path,
            minio_bucket=minio_bucket,
            chat_id=chat_id,
        )

        download_url = None
        if result.get("data"):
            download_url = result["data"].get("download_url")

        summary_parts = [f"status={result.get('status', 'unknown')}"]
        if download_url:
            summary_parts.append(f"download_url={download_url}")
        feishu_sent = result.get("data", {}).get("feishu_message_sent")
        if feishu_sent is not None:
            summary_parts.append(f"feishu_sent={feishu_sent}")

        return {
            "status": result.get("status", "success"),
            "message": result.get("message", ""),
            "download_url": download_url,
            "result_summary": ", ".join(summary_parts),
        }

    except Exception as e:
        logger.error(f"IT报告任务错误: {e}", extra={"action": "it_reporter.run"})
        return {"status": "failed", "error": str(e)}
