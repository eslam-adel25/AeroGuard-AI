import logging
import os
import smtplib
import socket
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def _get_smtp_config() -> dict:
    return {
        "host": os.getenv("SMTP_HOST"),
        "port": int(os.getenv("SMTP_PORT", "587")) if os.getenv("SMTP_PORT") else 587,
        "username": os.getenv("SMTP_USERNAME") or os.getenv("SMTP_USER"),
        "password": os.getenv("SMTP_PASSWORD") or os.getenv("SMTP_PASS"),
        "from_address": os.getenv("MAIL_FROM") or os.getenv("EMAIL_FROM") or "no-reply@aeroguard.local",
        "from_name": os.getenv("MAIL_FROM_NAME", "AeroGuard AI"),
        "frontend_base": os.getenv("FRONTEND_BASE", "http://localhost:5173"),
        "verification_expire_minutes": int(os.getenv("EMAIL_VERIFICATION_EXPIRE_MINUTES", "15")),
    }


def send_verification_email(to_email: str, full_name: str, token: str, otp_code: str | None = None):
    config = _get_smtp_config()
    code = otp_code or token
    link = f"{config['frontend_base']}/verify-email?email={to_email}"
    subject = "Verify your AeroGuard account"
    body = (
        f"Hello {full_name},\n\n"
        f"Please use the verification code below to activate your AeroGuard account:\n\n"
        f"Verification code: {code}\n\n"
        f"You can also open: {link}\n\n"
        f"This code expires in {config['verification_expire_minutes']} minutes.\n\n"
        "If you did not register, ignore this email.\n\n"
        "Regards,\n"
        "AeroGuard Team"
    )

    if config["host"] and config["port"] and config["username"] and config["password"]:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = f"{config['from_name']} <{config['from_address']}>"
        msg["To"] = to_email
        msg.set_content(body)

        try:
            original_getfqdn = socket.getfqdn
            socket.getfqdn = lambda name=None: "localhost"
            try:
                with smtplib.SMTP(
                    config["host"],
                    config["port"],
                    timeout=20,
                    local_hostname="localhost",
                ) as server:
                    server.starttls()
                    server.login(config["username"], config["password"])
                    server.send_message(msg)
            finally:
                socket.getfqdn = original_getfqdn
            logger.info("Verification email sent successfully to %s", to_email)
        except Exception:
            logger.exception("Failed to send verification email to %s", to_email)
            raise
    else:
        logger.warning("SMTP settings missing; printing verification email for %s", to_email)
        logger.info("[EMAIL] To: %s Subject: %s\n%s", to_email, subject, body)
