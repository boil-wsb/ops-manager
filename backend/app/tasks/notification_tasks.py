"""
Notification tasks.
"""

import asyncio
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from celery import shared_task
from sqlalchemy import select

from app.config import settings
from app.core.logging import get_logger
from app.tasks.utils import get_celery_async_session

logger = get_logger(__name__)


@shared_task(bind=True, max_retries=3)
def send_email_notification(
    self, to_addresses: list, subject: str, body: str, html_body: str = None
):
    """Send email notification."""
    try:
        if not settings.smtp_host:
            logger.warning("SMTP not configured, skipping email notification")
            return

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

        logger.info(f"Email notification sent: to={to_addresses}, subject={subject}")

    except Exception as exc:
        logger.error(f"Failed to send email notification: {str(exc)}")
        raise self.retry(exc=exc, countdown=60) from exc


@shared_task(bind=True, max_retries=3)
def send_webhook_notification(self, url: str, payload: dict, headers: dict = None):
    """Send webhook notification."""
    import httpx

    try:
        headers = headers or {}
        headers["Content-Type"] = "application/json"

        response = httpx.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()

        logger.info(f"Webhook notification sent: url={url}, status={response.status_code}")

    except Exception as exc:
        logger.error(f"Failed to send webhook notification: url={url}, error={str(exc)}")
        raise self.retry(exc=exc, countdown=60) from exc


@shared_task
def send_alert_notification(alert_id: int):
    """Send notification for an alert."""

    async def _send():
        from app.models.monitor import Alert, NotificationChannel

        session_local = get_celery_async_session()

        async with session_local() as db:
            result = await db.execute(select(Alert).where(Alert.id == alert_id))
            alert = result.scalar_one_or_none()

            if not alert:
                logger.warning(f"Alert {alert_id} not found")
                return

            result = await db.execute(
                select(NotificationChannel).where(NotificationChannel.is_enabled is True)
            )
            channels = result.scalars().all()

            for channel in channels:
                try:
                    if channel.channel_type.value == "email":
                        config = channel.config
                        to_addresses = config.get("to_addresses", [])
                        if to_addresses:
                            subject = f"[ALERT] {alert.title}"
                            body = f"""
Alert: {alert.title}
Severity: {alert.severity.value}
Status: {alert.status}
Message: {alert.message or "N/A"}
Time: {alert.started_at}
                            """
                            send_email_notification.delay(to_addresses, subject, body)

                    elif channel.channel_type.value == "webhook":
                        config = channel.config
                        url = config.get("url")
                        if url:
                            payload = {
                                "alert_id": alert.id,
                                "title": alert.title,
                                "severity": alert.severity.value,
                                "status": alert.status,
                                "message": alert.message,
                                "started_at": alert.started_at.isoformat(),
                            }
                            headers = config.get("headers", {})
                            send_webhook_notification.delay(url, payload, headers)

                except Exception as e:
                    logger.error(
                        f"Failed to send notification: channel={channel.name}, alert_id={alert_id}, error={str(e)}"
                    )

            alert.notification_sent = True
            await db.commit()

            logger.info(f"Alert notifications sent: alert_id={alert_id}")

    asyncio.run(_send())
