import bcrypt
from datetime import datetime, timedelta, timezone
from jose import jwt
import os
from dotenv import load_dotenv
import secrets
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Any

load_dotenv()

DEFAULT_SECRET = "super_secret"


def _get_secret_key() -> str:
    secret = os.getenv("SECRET_KEY") or os.getenv("JWT_SECRET") or DEFAULT_SECRET
    if secret == DEFAULT_SECRET:
        return secret
    return secret


def _get_algorithm() -> str:
    return os.getenv("ALGORITHM", "HS256")


def hash_password(password: str) -> str:
    """Hash passwords with bcrypt before persisting them."""
    if not isinstance(password, str) or len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    hashed_password = bcrypt.hashpw(pwd_bytes, salt)
    return hashed_password.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        if not isinstance(plain_password, str) or not isinstance(hashed_password, str):
            return False
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


def create_access_token(data: dict[str, Any]) -> str:
    to_encode = dict(data)
    expire = datetime.now(timezone.utc) + timedelta(minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, _get_secret_key(), algorithm=_get_algorithm())


def verify_token(token: str) -> Optional[dict[str, Any]]:
    try:
        if not isinstance(token, str) or not token.strip():
            return None
        payload = jwt.decode(token, _get_secret_key(), algorithms=[_get_algorithm()])
        if not isinstance(payload, dict):
            return None
        return payload
    except Exception:
        return None


def create_refresh_token_string(length: int = 48) -> str:
    if length <= 0:
        raise ValueError("Token length must be positive")
    return secrets.token_urlsafe(length)


http_bearer = HTTPBearer(auto_error=False)


def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = credentials.credentials
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload