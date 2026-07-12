import logging
import os
import random
from collections import defaultdict, deque
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from ...database.session import get_db
from ...models.models import User, Role
from ...schemas.schemas import UserRegister, UserLogin
from ...core.security import hash_password, verify_password, create_access_token
from ...core.security import create_refresh_token_string
from ...repositories.token_repository import TokenRepository
from ...repositories.activity_repository import ActivityRepository
from datetime import datetime, timedelta, timezone
from ...core.emailer import send_verification_email
from ...models.models import EmailVerificationToken, RefreshToken

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

AUTH_RATE_LIMIT_WINDOW_SECONDS = 900
AUTH_RATE_LIMIT_MAX_ATTEMPTS = 8
AUTH_REGISTER_LIMIT_WINDOW_SECONDS = 1800
AUTH_REGISTER_LIMIT_MAX_ATTEMPTS = 5
_AUTH_ATTEMPT_HISTORY: dict[str, deque[datetime]] = defaultdict(deque)


def should_require_email_verification() -> bool:
    value = (os.getenv("REQUIRE_EMAIL_VERIFICATION") or "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def _get_client_id(request: Optional[Request]) -> str:
    if request is None:
        return "unknown"
    return getattr(request.client, "host", "unknown") or "unknown"


def _check_rate_limit(key: str, window_seconds: int, max_attempts: int) -> None:
    now = datetime.utcnow()
    cutoff = now - timedelta(seconds=window_seconds)
    bucket = _AUTH_ATTEMPT_HISTORY[key]
    while bucket and bucket[0] < cutoff:
        bucket.popleft()
    if len(bucket) >= max_attempts:
        raise HTTPException(status_code=429, detail="Too many requests")
    bucket.append(now)


def _is_token_expired(expires_at: datetime) -> bool:
    if expires_at is None:
        return True

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    else:
        expires_at = expires_at.astimezone(timezone.utc)

    now = datetime.now(timezone.utc)
    return expires_at <= now


def _generate_verification_code(length: int = 6) -> str:
    return "".join(str(random.randint(0, 9)) for _ in range(length))


def _create_verification_token(db: Session, user: User) -> tuple[str, EmailVerificationToken]:
    token_repo = TokenRepository(db)
    token_str = create_refresh_token_string(32)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=int(os.getenv("EMAIL_VERIFICATION_EXPIRE_MINUTES", "15")))
    ev = EmailVerificationToken(user_id=user.user_id, token=token_str, expires_at=expires_at)
    token_repo.create_email_verification(ev)
    return token_str, ev


# 1. مسار تسجيل حساب جديد (Section 1)
@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, db: Session = Depends(get_db), request: Request = None):
    client_id = _get_client_id(request)
    _check_rate_limit(f"register:{client_id}", AUTH_REGISTER_LIMIT_WINDOW_SECONDS, AUTH_REGISTER_LIMIT_MAX_ATTEMPTS)

    # فحص تكرار اسم المستخدم أو الإيميل
    normalized_username = (payload.username or "").strip()
    normalized_email = (str(payload.email) or "").strip().lower()
    normalized_full_name = (payload.full_name or "").strip()
    normalized_phone = (payload.phone or "").strip()

    if not normalized_full_name:
        raise HTTPException(status_code=400, detail="Full name is required")
    if not normalized_username:
        raise HTTPException(status_code=400, detail="Username is required")
    if len(normalized_username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")
    if not normalized_email:
        raise HTTPException(status_code=400, detail="Email is required")
    if not normalized_phone:
        raise HTTPException(status_code=400, detail="Phone number is required")
    if not payload.password or len(payload.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    if db.query(User).filter(User.username == normalized_username).first():
        raise HTTPException(status_code=400, detail="Username already exists")
    if db.query(User).filter(User.email == normalized_email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    # جلب رتبة "Officer" كافتراضية للمسجلين الجدد
    default_role = db.query(Role).filter(Role.role_name == "Officer").first()
    if not default_role:
        default_role = Role(role_name="Officer")
        db.add(default_role)
        db.commit()
        db.refresh(default_role)

    require_email_verification = should_require_email_verification()

    # إنشاء المستخدم وتشفير كلمة السر
    new_user = User(
        full_name=payload.full_name,
        username=normalized_username,
        email=normalized_email,
        phone=payload.phone,
        organization=payload.organization,
        password_hash=hash_password(payload.password),
        role_id=default_role.role_id,
        status="Active" if not require_email_verification else "Pending",
        is_verified=not require_email_verification,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    if require_email_verification:
        token_str, ev = _create_verification_token(db, new_user)
        otp_code = _generate_verification_code()
        ev.otp_code = otp_code
        db.commit()
        db.refresh(ev)
        try:
            send_verification_email(new_user.email, new_user.full_name, token_str, otp_code)
        except Exception:
            logger.exception("Registration email verification failed for user %s", new_user.email)

    return {
        "status": "success",
        "message": "User registered successfully",
        "requires_verification": require_email_verification,
    }

# 2. مسار تسجيل الدخول (Section 1)
@router.post("/login")
def login(payload: UserLogin, db: Session = Depends(get_db), request: Request = None):
    client_id = _get_client_id(request)
    username_key = (payload.username or "").strip().lower()
    _check_rate_limit(f"login:{client_id}", AUTH_RATE_LIMIT_WINDOW_SECONDS, AUTH_RATE_LIMIT_MAX_ATTEMPTS)
    _check_rate_limit(f"login:user:{username_key}", AUTH_RATE_LIMIT_WINDOW_SECONDS, AUTH_RATE_LIMIT_MAX_ATTEMPTS)

    normalized_username = (payload.username or "").strip()
    user = db.query(User).filter(User.username == normalized_username).first()

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    if should_require_email_verification() and not user.is_verified:
        raise HTTPException(status_code=403, detail="Email not verified")
    
    # تحديث وقت آخر دخول (Section 3)
    user.last_login = datetime.utcnow()
    db.commit()

    # إنشاء التوكن (JWT)
    token = create_access_token(data={
        "user_id": str(user.user_id),
        "role": user.role.role_name,
        "username": user.username
    })

    # create refresh token record
    token_repo = TokenRepository(db)
    refresh_str = create_refresh_token_string(48)
    rt_expires = datetime.utcnow() + timedelta(days=7)
    rt = RefreshToken(user_id=user.user_id, token=refresh_str, expires_at=rt_expires)
    token_repo.create_refresh_token(rt)

    # Log activity
    activity_repo = ActivityRepository(db)
    try:
        activity_repo.log(str(user.user_id), "login", {"username": user.username}, ip=None, user_agent=None)
    except Exception:
        pass

    return {
        "access_token": token,
        "token_type": "bearer",
        "refresh_token": refresh_str,
        "user": {
            "user_id": user.user_id,
            "full_name": user.full_name,
            "username": user.username,
            "role": user.role.role_name
        }
    }


@router.post("/refresh")
def refresh_token(payload: dict, db: Session = Depends(get_db)):
    # expects {"refresh_token": "..."}
    token_value = payload.get("refresh_token")
    if not token_value:
        raise HTTPException(status_code=400, detail="Missing refresh_token")
    token_repo = TokenRepository(db)
    rt = token_repo.get_refresh_token(token_value)
    if not rt or rt.revoked:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    if rt.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Refresh token expired")

    user = db.query(User).filter(User.user_id == rt.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    access = create_access_token(data={
        "user_id": str(user.user_id),
        "role": user.role.role_name,
        "username": user.username
    })
    return {"access_token": access, "token_type": "bearer"}


@router.get("/verify")
def verify_email(token: str, db: Session = Depends(get_db)):
    token_repo = TokenRepository(db)
    ev = token_repo.get_email_verification(token)
    if not ev:
        raise HTTPException(status_code=404, detail="Invalid or expired verification token")
    if _is_token_expired(ev.expires_at):
        raise HTTPException(status_code=400, detail="Verification token expired")

    user = db.query(User).filter(User.user_id == ev.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    changed = False
    if getattr(ev, "new_email", None):
        if db.query(User).filter(User.email == ev.new_email).first():
            raise HTTPException(status_code=400, detail="Email already in use")
        user.email = ev.new_email
        changed = True
    if getattr(ev, "new_username", None):
        if db.query(User).filter(User.username == ev.new_username).first():
            raise HTTPException(status_code=400, detail="Username already in use")
        user.username = ev.new_username
        changed = True

    user.is_verified = True
    user.status = "Active"
    db.commit()
    token_repo.delete_email_verification(ev.token_id)

    try:
        act = ActivityRepository(db)
        act.log(str(user.user_id), "email_verified", {"changed": changed})
    except Exception:
        logger.exception("Failed to log verification activity for user %s", user.user_id)

    return {"status": "verified"}


@router.post("/verify-otp")
def verify_otp(payload: dict, db: Session = Depends(get_db)):
    email = (payload.get("email") or "").strip().lower()
    code = (payload.get("code") or "").strip()
    if not email or not code:
        raise HTTPException(status_code=400, detail="Email and verification code are required")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    ev = db.query(EmailVerificationToken).filter(EmailVerificationToken.user_id == user.user_id).order_by(EmailVerificationToken.created_at.desc()).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Verification code not found")
    if _is_token_expired(ev.expires_at):
        raise HTTPException(status_code=400, detail="Verification code expired")
    if ev.otp_code != code:
        raise HTTPException(status_code=400, detail="Invalid verification code")

    user.is_verified = True
    user.status = "Active"
    db.commit()
    db.delete(ev)
    db.commit()

    try:
        act = ActivityRepository(db)
        act.log(str(user.user_id), "email_verified_otp", {"email": email})
    except Exception:
        logger.exception("Failed to log OTP verification activity for user %s", user.user_id)

    return {"status": "verified"}


@router.post("/resend-verification")
def resend_verification(payload: dict, db: Session = Depends(get_db)):
    email = payload.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="email required")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_verified:
        return {"status": "already_verified"}
    token_repo = TokenRepository(db)
    existing = db.query(EmailVerificationToken).filter(EmailVerificationToken.user_id == user.user_id).first()
    if existing and existing.resend_count >= 3:
        raise HTTPException(status_code=429, detail="Resend limit reached")

    token_str = create_refresh_token_string(32)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=int(os.getenv("EMAIL_VERIFICATION_EXPIRE_MINUTES", "15")))
    if existing:
        existing.token = token_str
        existing.expires_at = expires_at
        existing.resend_count = (existing.resend_count or 0) + 1
        token_obj = existing
    else:
        token_obj = EmailVerificationToken(user_id=user.user_id, token=token_str, expires_at=expires_at, resend_count=1)
        token_repo.create_email_verification(token_obj)

    try:
        otp_code = _generate_verification_code()
        token_obj.otp_code = otp_code
        token_obj.expires_at = expires_at
        token_obj.resend_count = (token_obj.resend_count or 0) + 1
        db.commit()
        db.refresh(token_obj)
        send_verification_email(user.email, user.full_name, token_str, otp_code)
    except Exception:
        logger.exception("Failed to resend verification email for user %s", user.email)
        raise
    return {"status": "sent"}


@router.post("/logout")
def logout(payload: dict, db: Session = Depends(get_db)):
    # expects {"refresh_token": "..."}
    token_value = payload.get("refresh_token")
    if not token_value:
        return {"status": "ok"}
    token_repo = TokenRepository(db)
    token_repo.revoke_refresh_token(token_value)
    return {"status": "logged_out"}


@router.get("/create-admin")
def create_admin(db: Session = Depends(get_db)):

    users = db.query(User).all()

    return {
        "count": len(users),
        "users": [u.username for u in users]
    }