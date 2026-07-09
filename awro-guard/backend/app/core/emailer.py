import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587)) if os.getenv("SMTP_PORT") else None
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
FROM_ADDR = os.getenv("EMAIL_FROM", "no-reply@aeroguard.local")
FRONTEND_BASE = os.getenv("FRONTEND_BASE", "http://localhost:5173")


def send_verification_email(to_email: str, full_name: str, token: str):
    link = f"{FRONTEND_BASE}/verify-email?token={token}"
    subject = "Verify your AeroGuard account"
    body = f"Hello {full_name},\n\nPlease verify your email by clicking the link below:\n\n{link}\n\nThis link will expire in 24 hours.\n\nIf you did not register, ignore this email.\n\nRegards,\nAeroGuard Team"

    if SMTP_HOST and SMTP_PORT and SMTP_USER and SMTP_PASS:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = FROM_ADDR
        msg["To"] = to_email
        msg.set_content(body)

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
    else:
        # Fallback for development: print the link to logs
        print(f"[EMAIL] To: {to_email} Subject: {subject}\n{body}")
