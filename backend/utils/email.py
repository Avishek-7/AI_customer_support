import smtplib
from email.message import EmailMessage
from core.config import settings
from utils.logger import get_logger

logger = get_logger("backend.utils.email")


def _mask_email(email: str) -> str:
    if "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    local_masked = (local[:2] + "***") if len(local) > 2 else "***"
    return f"{local_masked}@{domain}"


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
        smtp_timeout = settings.SMTP_TIMEOUT if settings.SMTP_TIMEOUT is not None else 10
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=smtp_timeout) as smtp:
            if settings.SMTP_USE_TLS:
                smtp.starttls()
            if settings.SMTP_USER and settings.SMTP_PASS:
                smtp.login(settings.SMTP_USER, settings.SMTP_PASS)
            smtp.send_message(msg)
        logger.info("Password reset email sent", extra={"to_masked": _mask_email(to)})
        return True
    except Exception as e:
        logger.error("Failed to send password reset email", extra={"to_masked": _mask_email(to), "error": str(e)})
        return False
