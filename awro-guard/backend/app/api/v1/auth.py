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
from datetime import datetime, timedelta
from ...core.emailer import send_verification_email
from ...models.models import EmailVerificationToken, RefreshToken

router = APIRouter(prefix="/auth", tags=["Authentication"])

AUTH_RATE_LIMIT_WINDOW_SECONDS = 900
AUTH_RATE_LIMIT_MAX_ATTEMPTS = 8
AUTH_REGISTER_LIMIT_WINDOW_SECONDS = 1800
AUTH_REGISTER_LIMIT_MAX_ATTEMPTS = 5
_AUTH_ATTEMPT_HISTORY: dict[str, deque[datetime]] = defaultdict(deque)


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

# 1. مسار تسجيل حساب جديد (Section 1)
@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, db: Session = Depends(get_db), request: Optional[Request] = None):
    client_id = _get_client_id(request)
    _check_rate_limit(f"register:{client_id}", AUTH_REGISTER_LIMIT_WINDOW_SECONDS, AUTH_REGISTER_LIMIT_MAX_ATTEMPTS)

    # فحص تكرار اسم المستخدم أو الإيميل
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    # جلب رتبة "Officer" كافتراضية للمسجلين الجدد
    default_role = db.query(Role).filter(Role.role_name == "Officer").first()
    if not default_role:
        default_role = Role(role_name="Officer")
        db.add(default_role)
        db.commit()
        db.refresh(default_role)

    # إنشاء المستخدم وتشفير كلمة السر
    new_user = User(
        full_name=payload.full_name,
        username=payload.username,
        email=payload.email,
        phone=payload.phone,
        organization=payload.organization,
        password_hash=hash_password(payload.password),
        role_id=default_role.role_id,
        status="Pending",
        is_verified=False
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # create verification token
    token_repo = TokenRepository(db)
    token_str = create_refresh_token_string(32)
    expires_at = datetime.utcnow() + timedelta(hours=24)
    ev = EmailVerificationToken(user_id=new_user.user_id, token=token_str, expires_at=expires_at)
    token_repo.create_email_verification(ev)

    # send verification email (best-effort)
    try:
        send_verification_email(new_user.email, new_user.full_name, token_str)
    except Exception as exc:
        print(f"⚠️ Failed to send verification email: {exc}")
    return {"status": "success", "message": "User registered successfully"}

# 2. مسار تسجيل الدخول (Section 1)
@router.post("/login")
def login(payload: UserLogin, db: Session = Depends(get_db), request: Optional[Request] = None):
    client_id = _get_client_id(request)
    username_key = (payload.username or "").strip().lower()
    _check_rate_limit(f"login:{client_id}", AUTH_RATE_LIMIT_WINDOW_SECONDS, AUTH_RATE_LIMIT_MAX_ATTEMPTS)
    _check_rate_limit(f"login:user:{username_key}", AUTH_RATE_LIMIT_WINDOW_SECONDS, AUTH_RATE_LIMIT_MAX_ATTEMPTS)

    user = db.query(User).filter(User.username == payload.username).first()
    
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Email not verified")
    
    # تحديث وقت آخر دخول (Section 3)
    user.last_login = func.now()
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
    if ev.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Verification token expired")

    # mark user verified or apply pending email/username change
    user = db.query(User).filter(User.user_id == ev.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # handle email/username change requests
    changed = False
    if getattr(ev, "new_email", None):
        # ensure new email is not used
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

    # log activity
    try:
        act = ActivityRepository(db)
        act.log(str(user.user_id), "email_verified", {"changed": changed})
    except Exception:
        pass

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
    # find existing token and check resend count
    existing = db.query(EmailVerificationToken).filter(EmailVerificationToken.user_id == user.user_id).first()
    if existing and existing.resend_count >= 3:
        raise HTTPException(status_code=429, detail="Resend limit reached")
    token_str = create_refresh_token_string(32)
    expires_at = datetime.utcnow() + timedelta(hours=24)
    if existing:
        existing.token = token_str
        existing.expires_at = expires_at
        existing.resend_count = (existing.resend_count or 0) + 1
        db.commit()
        token_obj = existing
    else:
        token_obj = EmailVerificationToken(user_id=user.user_id, token=token_str, expires_at=expires_at, resend_count=1)
        token_repo.create_email_verification(token_obj)
    try:
        send_verification_email(user.email, user.full_name, token_str)
    except Exception as exc:
        print(f"⚠️ Failed to resend verification email: {exc}")
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