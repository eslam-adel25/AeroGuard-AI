from app.api.v1 import auth
from app.core import emailer


def test_email_verification_is_disabled_by_default(monkeypatch) -> None:
    monkeypatch.delenv("REQUIRE_EMAIL_VERIFICATION", raising=False)
    assert auth.should_require_email_verification() is False


def test_email_verification_can_be_enabled(monkeypatch) -> None:
    monkeypatch.setenv("REQUIRE_EMAIL_VERIFICATION", "true")
    assert auth.should_require_email_verification() is True


def test_verification_code_generation_is_numeric() -> None:
    code = auth._generate_verification_code()
    assert len(code) == 6
    assert code.isdigit()


def test_send_verification_email_uses_safe_local_hostname(monkeypatch) -> None:
    captured = {}

    class FakeSMTP:
        def __init__(self, host, port, timeout=None, local_hostname=None):
            captured["host"] = host
            captured["port"] = port
            captured["timeout"] = timeout
            captured["local_hostname"] = local_hostname

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def starttls(self):
            return None

        def login(self, username, password):
            return None

        def send_message(self, message):
            return None

    monkeypatch.setattr(emailer.smtplib, "SMTP", FakeSMTP)
    monkeypatch.setenv("SMTP_HOST", "smtp-relay.brevo.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USERNAME", "user")
    monkeypatch.setenv("SMTP_PASSWORD", "pass")
    monkeypatch.setenv("MAIL_FROM", "test@example.com")

    emailer.send_verification_email("user@example.com", "Test", "token", "123456")

    assert captured["local_hostname"] == "localhost"
