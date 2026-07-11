import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.security import (
    DEFAULT_DEMO_ACCOUNT_PASSWORD,
    hash_password,
    verify_password,
    create_access_token,
    verify_token,
    ensure_demo_user_password,
)
from app.models.models import User


def test_password_hash_round_trip():
    password = "StrongPass123!"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("wrong", hashed) is False


def test_jwt_round_trip_and_expiration():
    token = create_access_token({"sub": "user-1", "role": "Administrator"})
    assert verify_token(token) is not None
    assert verify_token(token + "x") is None
