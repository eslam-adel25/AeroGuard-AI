from datetime import datetime, timedelta, timezone

from app.api.v1.auth import _is_token_expired


def test_is_token_expired_accepts_naive_and_aware_datetimes() -> None:
    assert _is_token_expired(datetime.utcnow() - timedelta(minutes=1)) is True
    assert _is_token_expired(datetime.now(timezone.utc) + timedelta(minutes=1)) is False
