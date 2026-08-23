"""
Minimal email sender. If SMTP_HOST isn't configured (the default in
.env.example), emails are logged to the console instead of sent — this lets
you develop the full signup/reset flow locally without real SMTP credentials.
Swap in your provider's SDK (SES, Postmark, Resend, etc.) for production.
"""
import logging
import smtplib
from email.message import EmailMessage

from app.config import settings

logger = logging.getLogger("chatline.email")


def _send(to_email: str, subject: str, body: str) -> None:
    if not settings.smtp_host:
        logger.info(
            "\n----- DEV EMAIL (no SMTP configured) -----\n"
            "To: %s\nSubject: %s\n\n%s\n--------------------------------------------\n",
            to_email,
            subject,
            body,
        )
        return

    msg = EmailMessage()
    msg["From"] = settings.smtp_from_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.starttls()
        if settings.smtp_username:
            server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(msg)


def send_verification_email(to_email: str, raw_token: str) -> None:
    link = f"{settings.frontend_url}/verify-email?token={raw_token}"
    _send(
        to_email,
        f"Verify your {settings.app_name} account",
        f"Welcome to {settings.app_name}!\n\n"
        f"Confirm your email address by visiting:\n{link}\n\n"
        "This link expires in 24 hours. If you didn't create an account, ignore this email.",
    )


def send_password_reset_email(to_email: str, raw_token: str) -> None:
    link = f"{settings.frontend_url}/reset-password?token={raw_token}"
    _send(
        to_email,
        f"Reset your {settings.app_name} password",
        "We received a request to reset your password.\n\n"
        f"Choose a new password by visiting:\n{link}\n\n"
        "This link expires in 1 hour. If you didn't request this, you can safely ignore this email.",
    )
