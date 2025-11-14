import os
from email.message import EmailMessage

import aiosmtplib

from app.core.secrets import get_smtp_password, get_smtp_username

SMTP_HOST = os.getenv("SMTP_HOST", "mail")
SMTP_PORT = int(os.getenv("SMTP_PORT", "1025"))
SMTP_STARTTLS = os.getenv("SMTP_STARTTLS", "false").lower() == "true"
EMAIL_SENDER = os.getenv("EMAIL_SENDER", "noreply@fitfolio.local")


async def send_email(to: str, subject: str, body: str, *, sender: str | None = None):
    msg = EmailMessage()
    msg["From"] = sender or EMAIL_SENDER
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    # Lazy-load SMTP credentials from secrets/env
    smtp_username = get_smtp_username()
    smtp_password = get_smtp_password()

    await aiosmtplib.send(
        msg,
        hostname=SMTP_HOST,
        port=SMTP_PORT,
        username=smtp_username,
        password=smtp_password,
        start_tls=SMTP_STARTTLS,
    )
