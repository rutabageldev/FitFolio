import os
from email.message import EmailMessage

import aiosmtplib

SMTP_HOST = os.getenv("SMTP_HOST", "mail")
SMTP_PORT = int(os.getenv("SMTP_PORT", "1025"))
SMTP_STARTTLS = os.getenv("SMTP_STARTTLS", "false").lower() == "true"
SMTP_USERNAME = os.getenv("SMTP_USERNAME") or None
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD") or None
EMAIL_SENDER = os.getenv("EMAIL_SENDER", "noreply@fitfolio.local")


async def send_email(to: str, subject: str, body: str, *, sender: str | None = None):
    msg = EmailMessage()
    msg["From"] = sender or EMAIL_SENDER
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    await aiosmtplib.send(
        msg,
        hostname=SMTP_HOST,
        port=SMTP_PORT,
        username=SMTP_USERNAME,
        password=SMTP_PASSWORD,
        start_tls=SMTP_STARTTLS,
    )
