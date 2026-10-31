import logging
import os
import secrets
from collections import defaultdict, deque
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from ...database.session import get_db
from ...models.models import CustomerProfile, User, Role
from ...schemas.schemas import UserRegister, UserLogin
from ...core.security import hash_password, verify_password, create_access_token
from ...core.auth_middleware import get_authenticated_user, user_access_metadata
from ...core.tenant import customer_profile_for_user
from ...core.customer_features import enabled_customer_features
from ...utils.device_info import parse_user_agent
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


def is_grandfathered_platform_customer(profile: CustomerProfile | None) -> bool:
    return bool(
        profile
        and profile.workflow_status == "PLATFORM_CUSTOMER"
        and profile.account_status == "ACTIVE"
    )


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
    return "".join(str(secrets.randbelow(10)) for _ in range(length))


def _create_verification_token(db: Session, user: User) -> tuple[str, EmailVerificationToken]:
    token_str = create_refresh_token_string(32)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=int(os.getenv("EMAIL_VERIFICATION_EXPIRE_MINUTES", "15")))
    ev = EmailVerificationToken(user_id=user.user_id, token=token_str, expires_at=expires_at)
    db.add(ev)
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

    require_email_verification = should_require_email_verification()
    try:
        if db.query(User).filter(User.username == normalized_username).first():
            raise HTTPException(status_code=400, detail="Username already exists")
        if db.query(User).filter(User.email == normalized_email).first():
            raise HTTPException(status_code=400, detail="Email already registered")

        default_role = db.query(Role).filter(Role.role_name == "Admin").first()
        if not default_role:
            default_role = Role(role_name="Admin")
            db.add(default_role)
            db.flush()

        new_user = User(
            full_name=normalized_full_name,
            username=normalized_username,
            email=normalized_email,
            phone=normalized_phone,
            organization=payload.organization,
            password_hash=hash_password(payload.password),
            role_id=default_role.role_id,
            status="Pending",
            is_verified=not require_email_verification,
        )
        db.add(new_user)
        db.flush()
        profile = CustomerProfile(
            user_id=new_user.user_id,
            workflow_status=(
                "AWAITING_EMAIL_VERIFICATION"
                if require_email_verification
                else "UNREAD"
            ),
            account_status="PENDING",
        )
        db.add(profile)
        db.flush()
        new_user.customer_profile_id = profile.customer_profile_id

        token_str = None
        otp_code = None
        if require_email_verification:
            token_str, ev = _create_verification_token(db, new_user)
            otp_code = _generate_verification_code()
            ev.otp_code = otp_code
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        logger.info("Registration rejected by a uniqueness constraint")
        raise HTTPException(status_code=400, detail="Username or email already registered") from exc

    if token_str and otp_code:
        try:
            send_verification_email(new_user.email, new_user.full_name, token_str, otp_code)
        except Exception:
            logger.exception(
                "Registration email verification failed for user %s",
                new_user.email,
            )

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
    if (
        should_require_email_verification()
        and not user.is_verified
        and not is_grandfathered_platform_customer(
            customer_profile_for_user(user) or user.customer_profile
        )
    ):
        raise HTTPException(status_code=403, detail="Email not verified")

    if user.role is None:
        raise HTTPException(status_code=403, detail="User role is not configured")
    
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
    device_info = parse_user_agent(request.headers.get("user-agent") if request else None)
    rt = RefreshToken(
        user_id=user.user_id,
        token=refresh_str,
        expires_at=rt_expires,
        user_agent=request.headers.get("user-agent") if request else None,
        operating_system=device_info.get("operating_system"),
        browser=device_info.get("browser"),
        device_category=device_info.get("device_category"),
        device_type=device_info.get("device_type"),
        device_model=device_info.get("device_model"),
    )
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
            **user_access_metadata(user),
        }
    }


@router.get("/me")
async def get_my_authentication_state(
    current_user: dict = Depends(get_authenticated_user),
    db: Session = Depends(get_db),
):
    identity = {key: value for key, value in current_user.items() if key != "_user"}
    identity["enabled_features"] = enabled_customer_features(
        db, str(current_user["user_id"]), current_user.get("role")
    )
    return identity


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
        raise HTTPException(status_code=401, detail="User no longer exists")
    if user.role is None:
        raise HTTPException(status_code=403, detail="User role is not configured")
    profile = customer_profile_for_user(user) or user.customer_profile
    is_legacy_active = is_grandfathered_platform_customer(profile)
    if profile and profile.account_status == "INACTIVE":
        raise HTTPException(status_code=403, detail="Account is inactive")
    if (
        should_require_email_verification()
        and not user.is_verified
        and not is_legacy_active
    ):
        raise HTTPException(status_code=403, detail="Email not verified")
    if profile and profile.account_status not in {"ACTIVE", "PENDING"}:
        raise HTTPException(status_code=403, detail="Account is inactive")

    access = create_access_token(data={
        "user_id": str(user.user_id),
        "role": user.role.role_name,
        "username": user.username
    })
    return {"access_token": access, "token_type": "bearer"}


@router.get("/verify")
def verify_email(token: str, db: Session = Depends(get_db)):
    ev = (
        db.query(EmailVerificationToken)
        .filter(EmailVerificationToken.token == token)
        .with_for_update()
        .first()
    )
    if not ev:
        raise HTTPException(status_code=404, detail="Invalid or expired verification token")
    if _is_token_expired(ev.expires_at):
        raise HTTPException(status_code=400, detail="Verification token expired")

    user = (
        db.query(User)
        .filter(User.user_id == ev.user_id)
        .with_for_update()
        .first()
    )
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
    profile = db.query(CustomerProfile).filter(
        CustomerProfile.user_id == user.user_id
    ).with_for_update().first()
    if (
        profile
        and not changed
        and profile.workflow_status == "AWAITING_EMAIL_VERIFICATION"
    ):
        profile.workflow_status = "UNREAD"
        profile.account_status = "PENDING"
    db.delete(ev)
    db.commit()

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

    user = (
        db.query(User)
        .filter(User.email == email)
        .with_for_update()
        .first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    ev = (
        db.query(EmailVerificationToken)
        .filter(EmailVerificationToken.user_id == user.user_id)
        .order_by(EmailVerificationToken.created_at.desc())
        .with_for_update()
        .first()
    )
    if not ev:
        if user.is_verified:
            return {"status": "already_verified"}
        raise HTTPException(status_code=404, detail="Verification code not found")
    if _is_token_expired(ev.expires_at):
        raise HTTPException(status_code=400, detail="Verification code expired")
    if ev.otp_code != code:
        raise HTTPException(status_code=400, detail="Invalid verification code")

    user.is_verified = True
    profile = db.query(CustomerProfile).filter(
        CustomerProfile.user_id == user.user_id
    ).with_for_update().first()
    if profile and profile.workflow_status == "AWAITING_EMAIL_VERIFICATION":
        profile.workflow_status = "UNREAD"
        profile.account_status = "PENDING"
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
