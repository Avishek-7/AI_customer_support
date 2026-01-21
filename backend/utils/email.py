import smtplib
from email.message import EmailMessage
from core.config import settings
from utils.logger import get_logger

logger = get_logger("backend.utils.email")


def send_reset_email(to: str, reset_token: str):
    """Send password reset email with reset link."""
    reset_link = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
    
    msg = EmailMessage()
    msg["Subject"] = "Reset your password"
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to
    msg.set_content(
        f"""
Hi,

Click the link below to reset your password:

{reset_link}

This link will expire in 1 hour.

If you didn't request this, please ignore this email.
"""
    )

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as smtp:
            if settings.SMTP_USER and settings.SMTP_PASS:
                smtp.starttls()
                smtp.login(settings.SMTP_USER, settings.SMTP_PASS)
            smtp.send_message(msg)
        logger.info("Password reset email sent", extra={"to": to})
        return True
    except Exception as e:
        logger.error("Failed to send password reset email", extra={"to": to, "error": str(e)})
        return False
