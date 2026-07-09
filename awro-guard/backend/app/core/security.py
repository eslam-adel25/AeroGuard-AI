import bcrypt
from datetime import datetime, timedelta
from jose import jwt
import os
from dotenv import load_dotenv
import secrets
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional

load_dotenv()

# --- دالة تشفير كلمة المرور (هذه هي الدالة الناقصة) ---
def hash_password(password: str) -> str:
    """تحويل كلمة السر لنص مشفر (Hash) قبل الحفظ في الـ DB"""
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(pwd_bytes, salt)
    return hashed_password.decode('utf-8')

# --- دالة التحقق من كلمة المرور عند الدخول ---
def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'), 
            hashed_password.encode('utf-8')
        )
    except Exception as e:
        print(f"❌ Verification Error: {e}")
        return False

# --- دالة إنشاء توكن الدخول (JWT) ---
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60)))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, os.getenv("SECRET_KEY", "super_secret"), algorithm=os.getenv("ALGORITHM", "HS256"))

# --- دالة فك تشفير التوكن (للميدل وير) ---
def verify_token(token: str):
    try:
        secret_key = os.getenv("SECRET_KEY", "super_secret")
        algorithm = os.getenv("ALGORITHM", "HS256")
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        return payload
    except Exception:
        return None


# --- Refresh token helpers (stateless token string generation) ---
def create_refresh_token_string(length: int = 48) -> str:
    return secrets.token_urlsafe(length)


# --- Dependency helper to protect routes ---
http_bearer = HTTPBearer(auto_error=False)

def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = credentials.credentials
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload