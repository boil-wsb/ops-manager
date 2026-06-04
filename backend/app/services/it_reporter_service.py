import os
from urllib.parse import quote

from app.config import settings
from app.core.logging import get_logger
from app.db.session import db_operation_with_retry
from app.integrations.feishu.service import get_feishu_service
from app.integrations.minio.client import download_file, get_file_size
from app.services.report_parser import build_inspection_card_elements, parse_health_check_report

logger = get_logger(__name__)


def _build_download_url(minio_bucket: str, report_path: str) -> str:
    base_url = settings.itreporter_download_base_url.rstrip("/")
    return (
        f"{base_url}/api/v1/it-reporter/download"
        f"?bucket={quote(minio_bucket, safe='')}"
        f"&path={quote(report_path, safe='')}"
        f"&expires_hours={settings.itreporter_presigned_url_expires_hours}"
    )


class ITReporterService:
    async def process_report(
        self, report_path: str, minio_bucket: str, chat_id: str | None = None
    ) -> dict:
        local_filepath = download_file(minio_bucket, report_path)

        download_url = _build_download_url(minio_bucket, report_path)

        file_size = get_file_size(local_filepath)
        file_size_mb = round(file_size / (1024 * 1024), 2)

        report_data = None
        try:
            with open(local_filepath, encoding="utf-8") as f:
                html_content = f.read()
            report_data = parse_health_check_report(html_content)
            if report_data:
                logger.info(
                    f"报告解析完成: ok={report_data['ok_count']}, warning={report_data['warning_count']}, critical={report_data['critical_count']}",
                    extra={
                        "action": "it_reporter.run",
                        "ok": report_data["ok_count"],
                        "warning": report_data["warning_count"],
                        "critical": report_data["critical_count"],
                    },
                )
            else:
                logger.warning("报告解析结果为空", extra={"action": "it_reporter.run"})
        except Exception as e:
            logger.error(f"报告解析失败: {e}", extra={"action": "it_reporter.run"})

        card_elements, card_template = build_inspection_card_elements(
            report_data,
            download_url,
            file_size_mb,
            report_path,
            expires_hours=settings.itreporter_presigned_url_expires_hours,
        )

        feishu_card_message = {
            "schema": "2.0",
            "header": {
                "title": {"tag": "plain_text", "content": "📊 IT系统健康巡检报告"},
                "subtitle": {"tag": "plain_text", "content": os.path.basename(report_path)},
                "template": card_template,
            },
            "body": {"elements": card_elements},
            "config": {"update_multi": True},
        }

        feishu_sent = False
        if download_url and chat_id:
            try:
                feishu_service = get_feishu_service()
                feishu_service.send_message_to_user(
                    user_id=chat_id,
                    msg_type="interactive",
                    content=feishu_card_message,
                    receive_id_type="chat_id",
                )
                feishu_sent = True
                logger.info(
                    f"飞书通知已发送: chat_id={chat_id}",
                    extra={"action": "it_reporter.notify", "chat_id": chat_id},
                )
            except Exception as e:
                logger.error(f"飞书通知发送失败: {e}", extra={"action": "it_reporter.notify"})

        try:
            if os.path.exists(local_filepath):
                os.remove(local_filepath)
        except Exception:
            pass

        return {
            "status": "success",
            "message": "Report processed successfully",
            "data": {
                "file_size": file_size,
                "download_url": download_url,
                "url_expires_in": f"{settings.itreporter_presigned_url_expires_hours}小时（自动续期）",
                "feishu_message_sent": feishu_sent,
            },
        }

    async def get_chat_id_from_config(self) -> str | None:
        from app.crud.crud_system_config import crud_system_config

        async def _get_chat_id_db(db):
            return await crud_system_config.get_value(db, "itreporter.chat_id")

        try:
            return await db_operation_with_retry(
                _get_chat_id_db,
                max_retries=3,
                retry_delay=2.0,
            )
        except Exception as e:
            logger.error(f"查询飞书通知群聊 ID 失败: {e}", extra={"action": "it_reporter.config"})
            return None


it_reporter_service = ITReporterService()
