import asyncio
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from tenacity import retry, stop_after_attempt, wait_fixed

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@retry(stop=stop_after_attempt(3), wait=wait_fixed(60))
async def send_email_notification(
    to_addresses: list, subject: str, body: str, html_body: str = None
):
    try:
        if not settings.smtp_host:
            logger.warning("SMTP未配置，跳过邮件通知", extra={"action": "alert.notify"})
            return

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _send_email_sync, to_addresses, subject, body, html_body)

        logger.info(
            "邮件通知已发送",
            extra={"action": "alert.notify", "to": to_addresses, "subject": subject},
        )

    except Exception as exc:
        logger.error(f"邮件通知发送失败: {str(exc)}", extra={"action": "alert.notify"})
        raise


def _send_email_sync(to_addresses: list, subject: str, body: str, html_body: str = None):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_user
    msg["To"] = ", ".join(to_addresses)

    msg.attach(MIMEText(body, "plain"))
    if html_body:
        msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        if settings.smtp_tls:
            server.starttls()
        if settings.smtp_user and settings.smtp_password:
            server.login(settings.smtp_user, settings.smtp_password)
        server.sendmail(settings.smtp_user, to_addresses, msg.as_string())


@retry(stop=stop_after_attempt(3), wait=wait_fixed(60))
async def send_webhook_notification(url: str, payload: dict, headers: dict = None):
    import httpx

    try:
        headers = headers or {}
        headers["Content-Type"] = "application/json"

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()

        logger.info(
            "Webhook通知已发送",
            extra={"action": "alert.notify", "url": url, "status": response.status_code},
        )

    except Exception as exc:
        logger.error(
            f"Webhook通知发送失败: {str(exc)}", extra={"action": "alert.notify", "url": url}
        )
        raise
