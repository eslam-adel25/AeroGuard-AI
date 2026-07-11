from app.api.v1 import auth


def test_email_verification_is_disabled_by_default(monkeypatch) -> None:
    monkeypatch.delenv("REQUIRE_EMAIL_VERIFICATION", raising=False)
    assert auth.should_require_email_verification() is False


def test_email_verification_can_be_enabled(monkeypatch) -> None:
    monkeypatch.setenv("REQUIRE_EMAIL_VERIFICATION", "true")
    assert auth.should_require_email_verification() is True
