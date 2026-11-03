"""Alert fan-out: Slack webhook and SMTP email. Alerts are always written to
the DB first (delivery plane of record); channels are best-effort on top.
"""

import logging
import smtplib
from email.mime.text import MIMEText

import httpx

from app.config import settings

log = logging.getLogger(__name__)


async def deliver_slack(title: str, body: str) -> bool:
    if not settings.slack_webhook_url:
        return False
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                settings.slack_webhook_url,
                json={"text": f"*{title}*\n{body[:2800]}"},
            )
            return resp.status_code == 200
    except Exception as exc:
        log.warning("slack delivery failed: %s", exc)
        return False


async def deliver_email(title: str, body: str) -> bool:
    if not (settings.smtp_host and settings.alert_email_to):
        return False
    try:
        msg = MIMEText(body)
        msg["Subject"] = title
        msg["From"] = settings.alert_email_from
        msg["To"] = settings.alert_email_to
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
            smtp.starttls()
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)
        return True
    except Exception as exc:
        log.warning("email delivery failed: %s", exc)
        return False
