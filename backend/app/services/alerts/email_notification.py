"""
Email notification service.
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class EmailNotificationService:
    """Service for sending email notifications."""

    def __init__(self):
        """Initialize email service with SMTP settings."""
        self.smtp_host = settings.smtp_host
        self.smtp_port = settings.smtp_port
        self.smtp_user = settings.smtp_user
        self.smtp_password = settings.smtp_password
        self.smtp_tls = settings.smtp_tls

    def is_configured(self) -> bool:
        """Check if email service is properly configured."""
        return bool(self.smtp_host and self.smtp_user)

    def build_email_html(
        self,
        alertname: str,
        status: str,
        severity: str,
        instance: str,
        description: str,
        starts_at: str,
        annotations: dict[str, Any],
    ) -> str:
        """Build HTML email body for alert notification.

        Args:
            alertname: Alert name
            status: Alert status (firing/resolved)
            severity: Alert severity
            instance: Instance identifier
            description: Alert description
            starts_at: Alert start time
            annotations: Alert annotations

        Returns:
            HTML email body
        """
        status_color = "#dc3545" if status == "firing" else "#28a745"

        summary = annotations.get("summary", "")
        detail = annotations.get("detail", description)

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .header {{ background-color: {status_color}; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
                .header h1 {{ margin: 0; font-size: 24px; }}
                .content {{ padding: 20px; }}
                .field {{ margin-bottom: 15px; }}
                .field-label {{ font-weight: bold; color: #333; margin-bottom: 5px; }}
                .field-value {{ color: #666; }}
                .badge {{ display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 12px; color: white; }}
                .badge-critical {{ background-color: #dc3545; }}
                .badge-warning {{ background-color: #ffc107; color: #333; }}
                .badge-info {{ background-color: #17a2b8; }}
                .description {{ background-color: #f8f9fa; padding: 15px; border-radius: 4px; border-left: 4px solid {status_color}; }}
                .footer {{ padding: 15px; text-align: center; color: #999; font-size: 12px; border-top: 1px solid #eee; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>[{status.upper()}] {alertname}</h1>
                </div>
                <div class="content">
                    <div class="field">
                        <div class="field-label">Severity</div>
                        <div class="field-value">
                            <span class="badge badge-{severity}">{severity.upper()}</span>
                        </div>
                    </div>
                    <div class="field">
                        <div class="field-label">Instance</div>
                        <div class="field-value">{instance}</div>
                    </div>
                    <div class="field">
                        <div class="field-label">Start Time</div>
                        <div class="field-value">{starts_at}</div>
                    </div>
                    <div class="field">
                        <div class="field-label">Summary</div>
                        <div class="field-value">{summary}</div>
                    </div>
                    <div class="field">
                        <div class="field-label">Description</div>
                        <div class="description">{detail}</div>
                    </div>
                </div>
                <div class="footer">
                    This is an automated alert notification from OpsManager.
                </div>
            </div>
        </body>
        </html>
        """
        return html

    def build_email_text(
        self,
        alertname: str,
        status: str,
        severity: str,
        instance: str,
        description: str,
        starts_at: str,
        annotations: dict[str, Any],
    ) -> str:
        """Build plain text email body for alert notification.

        Args:
            alertname: Alert name
            status: Alert status
            severity: Alert severity
            instance: Instance identifier
            description: Alert description
            starts_at: Alert start time
            annotations: Alert annotations

        Returns:
            Plain text email body
        """
        summary = annotations.get("summary", "")
        detail = annotations.get("detail", description)

        text = f"""
[{status.upper()}] {alertname}
========================

Severity: {severity.upper()}
Instance: {instance}
Start Time: {starts_at}

Summary:
{summary}

Description:
{detail}

---
This is an automated alert notification from OpsManager.
        """
        return text.strip()

    def send_email(
        self,
        to_addresses: list[str],
        subject: str,
        body: str,
        html_body: str | None = None,
    ) -> bool:
        """Send an email notification.

        Args:
            to_addresses: List of recipient email addresses
            subject: Email subject
            body: Plain text body
            html_body: Optional HTML body

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.is_configured():
            logger.warning("Email service not configured, skipping email")
            return False

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.smtp_user
            msg["To"] = ", ".join(to_addresses)

            msg.attach(MIMEText(body, "plain"))
            if html_body:
                msg.attach(MIMEText(html_body, "html"))

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.smtp_tls:
                    server.starttls()
                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.smtp_user, to_addresses, msg.as_string())

            logger.info(f"Email sent successfully: to={to_addresses}, subject={subject}")
            return True

        except Exception as exc:
            logger.error(f"Failed to send email: to={to_addresses}, error={str(exc)}")
            return False

    def send_alert_email(
        self,
        to_addresses: list[str],
        alertname: str,
        status: str,
        severity: str,
        instance: str,
        description: str,
        starts_at: str,
        annotations: dict[str, Any],
    ) -> bool:
        """Send an alert notification email.

        Args:
            to_addresses: List of recipient email addresses
            alertname: Alert name
            status: Alert status
            severity: Alert severity
            instance: Instance identifier
            description: Alert description
            starts_at: Alert start time
            annotations: Alert annotations

        Returns:
            True if sent successfully, False otherwise
        """
        subject = f"[{status.upper()}] {severity.upper()} - {alertname}"
        body = self.build_email_text(
            alertname=alertname,
            status=status,
            severity=severity,
            instance=instance,
            description=description,
            starts_at=starts_at,
            annotations=annotations,
        )
        html_body = self.build_email_html(
            alertname=alertname,
            status=status,
            severity=severity,
            instance=instance,
            description=description,
            starts_at=starts_at,
            annotations=annotations,
        )

        return self.send_email(to_addresses, subject, body, html_body)


# Global service instance
email_notification_service = EmailNotificationService()
