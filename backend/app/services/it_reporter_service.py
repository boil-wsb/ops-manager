import os

from app.config import settings
from app.core.logging import get_logger
from app.db.session import get_session_maker
from app.integrations.feishu.service import get_feishu_service
from app.integrations.minio.client import download_file, generate_presigned_url, get_file_size
from app.services.report_parser import build_inspection_card_elements, parse_health_check_report

logger = get_logger(__name__)


class ITReporterService:
    async def process_report(
        self, report_path: str, minio_bucket: str, chat_id: str | None = None
    ) -> dict:
        local_filepath = download_file(minio_bucket, report_path)

        presigned_url = generate_presigned_url(minio_bucket, report_path, expires_hours=settings.itreporter_presigned_url_expires_hours)

        file_size = get_file_size(local_filepath)
        file_size_mb = round(file_size / (1024 * 1024), 2)

        report_data = None
        try:
            with open(local_filepath, encoding="utf-8") as f:
                html_content = f.read()
            report_data = parse_health_check_report(html_content)
            if report_data:
                logger.info(
                    f"Report parsed: ok={report_data['ok_count']}, "
                    f"warning={report_data['warning_count']}, "
                    f"critical={report_data['critical_count']}"
                )
            else:
                logger.warning("Report parsing returned empty result")
        except Exception as e:
            logger.error(f"Failed to parse report: {e}")

        card_elements, card_template = build_inspection_card_elements(
            report_data, presigned_url, file_size_mb, report_path,
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
        if presigned_url and chat_id:
            try:
                feishu_service = get_feishu_service()
                feishu_service.send_message_to_user(
                    user_id=chat_id,
                    msg_type="interactive",
                    content=feishu_card_message,
                    receive_id_type="chat_id",
                )
                feishu_sent = True
                logger.info(f"Feishu notification sent to chat_id={chat_id}")
            except Exception as e:
                logger.error(f"Failed to send Feishu notification: {e}")

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
                "presigned_url": presigned_url,
                "url_expires_in": f"{settings.itreporter_presigned_url_expires_hours}小时" if presigned_url else None,
                "feishu_message_sent": feishu_sent,
            },
        }

    async def get_chat_id_from_config(self) -> str | None:
        from app.crud.crud_system_config import crud_system_config

        session_maker = get_session_maker()
        async with session_maker() as db:
            return await crud_system_config.get_value(db, "itreporter.chat_id")


it_reporter_service = ITReporterService()
