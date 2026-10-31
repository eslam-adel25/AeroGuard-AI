import os
import uuid
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_

from ...database.session import get_db
from ...models.models import CustomerProfile, User, Role
from ...schemas.schemas import (
    UserResponse,
    UserCreate,
    RoleResponse,
    UserProfileUpdate,
    PasswordChangeRequest,
)
from ...core.auth_middleware import (
    get_self_service_user,
    require_tenant_isolation,
    role_required,
)
from ...core.tenant import tenant_member_user_ids
from ...core.security import hash_password, verify_password
from ...repositories.activity_repository import ActivityRepository
from ...repositories.token_repository import TokenRepository
from ...core.emailer import send_verification_email
from .uploads import resolve_upload_file
from ...models.models import EmailVerificationToken, RefreshToken
from datetime import datetime, timedelta
from ...core.security import create_refresh_token_string
from ...core.customer_features import (
    has_customer_feature,
)

router = APIRouter(prefix="/users", tags=["Users & Profile"])

# المجلد الخاص بصور الملف الشخصي
BASE_DIR = Path(__file__).resolve().parents[3]
UPLOAD_DIR = BASE_DIR / "uploads" / "avatars"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_AVATAR_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
MAX_AVATAR_SIZE = 5 * 1024 * 1024


async def require_profile_access(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_self_service_user),
):
    if current_user.get("role") != "Owner" and not has_customer_feature(
        db, current_user["user_id"], current_user.get("role"), "profile"
    ):
        raise HTTPException(
            status_code=403,
            detail="The profile feature is not enabled for this customer",
        )
    return current_user


# ==========================================
# 1. مسارات الملف الشخصي (User Profile - Self)
# ==========================================

@router.get("/profile", response_model=UserResponse)
async def get_my_profile(
    db: Session = Depends(get_db), 
    current_user: dict = Depends(require_profile_access),
):
    """جلب بيانات الموظف المسجل حالياً (صاحب التوكن)"""
    user = db.query(User).options(joinedload(User.role)).filter(User.user_id == current_user['user_id']).first()
    if not user:
        raise HTTPException(status_code=404, detail="User profile not found")
    return UserResponse.from_orm(user).dict()


@router.get("/profile/avatar")
def get_my_avatar(
    db: Session = Depends(get_db),
    identity: dict = Depends(get_self_service_user),
):
    user = db.query(User).filter(User.user_id == identity["user_id"]).first()
    if identity.get("role") != "Owner" and not has_customer_feature(
        db, identity["user_id"], identity.get("role"), "profile"
    ):
        raise HTTPException(
            status_code=403,
            detail="The profile feature is not enabled for this customer",
        )
    if not user or not user.profile_picture:
        raise HTTPException(status_code=404, detail="Avatar not found")
    prefix = "/uploads/avatars/"
    if not user.profile_picture.startswith(prefix):
        raise HTTPException(status_code=404, detail="Avatar not found")
    filename = user.profile_picture.removeprefix(prefix)
    if not filename or Path(filename).name != filename:
        raise HTTPException(status_code=404, detail="Avatar not found")
    path = resolve_upload_file(f"avatars/{filename}")
    if path is None:
        raise HTTPException(status_code=404, detail="Avatar not found")
    return FileResponse(path, headers={"Cache-Control": "private, no-store"})


@router.put("/profile", response_model=UserResponse)
async def update_my_profile(
    payload: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_profile_access),
):
    """تعديل الموظف لبياناته الشخصية (الاسم، الإيميل، الهاتف)"""
    user = db.query(User).filter(User.user_id == current_user['user_id']).first()

    # Email/username changes require verification
    if payload.email and payload.email != user.email:
        if db.query(User).filter(User.email == payload.email).first():
            raise HTTPException(status_code=400, detail="Email already in use")
        token_repo = TokenRepository(db)
        token_str = create_refresh_token_string(40)
        expires_at = datetime.utcnow() + timedelta(hours=24)
        ev = EmailVerificationToken(user_id=user.user_id, token=token_str, expires_at=expires_at, new_email=payload.email)
        token_repo.create_email_verification(ev)
        try:
            send_verification_email(payload.email, user.full_name, token_str)
        except Exception:
            pass
        # do not update user.email until verified

    if payload.full_name:
        user.full_name = payload.full_name
    if payload.phone:
        user.phone = payload.phone
    if payload.organization is not None:
        user.organization = payload.organization
    
    db.commit()
    db.refresh(user)

    # log activity
    try:
        act = ActivityRepository(db)
        act.log(str(user.user_id), "profile_updated", {"changed_fields": [k for k,v in payload.dict(exclude_none=True).items()]})
    except Exception:
        pass

    return UserResponse.from_orm(user).dict()

@router.put("/profile/password")
@router.post("/profile/password")
async def change_my_password(
    payload: PasswordChangeRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_self_service_user)
):
    """تغيير كلمة المرور بعد التحقق من القديمة (Section 3)"""
    user = db.query(User).filter(User.user_id == current_user['user_id']).first()

    if not verify_password(payload.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password incorrect")

    user.password_hash = hash_password(payload.new_password)
    db.commit()
    # revoke all refresh tokens (logout all sessions)
    try:
        token_repo = TokenRepository(db)
        tokens = db.query(RefreshToken).filter(RefreshToken.user_id == user.user_id).all()
        for t in tokens:
            t.revoked = True
        db.commit()
    except Exception:
        pass

    try:
        act = ActivityRepository(db)
        act.log(str(user.user_id), "password_changed", {})
    except Exception:
        pass

    return {"status": "success", "message": "Password updated successfully"}

@router.post("/profile/avatar")
async def upload_my_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_profile_access),
):
    """رفع صورة شخصية (Avatar) وحفظ المسار (Section 3)"""
    user = db.query(User).filter(User.user_id == current_user['user_id']).first()
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="Invalid file name")

    file_name = Path(file.filename).name
    file_ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
    if file_ext not in ALLOWED_AVATAR_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Invalid file type")

    contents = await file.read()
    if len(contents) > MAX_AVATAR_SIZE:
        raise HTTPException(status_code=400, detail="File too large")

    safe_name = f"{user.user_id}_{uuid.uuid4().hex[:8]}.{file_ext}"
    file_path = UPLOAD_DIR / safe_name
    with file_path.open("wb") as f:
        f.write(contents)

    if user.profile_picture:
        try:
            old_path = Path(user.profile_picture)
            if old_path.exists() and old_path.parent == UPLOAD_DIR:
                old_path.unlink()
        except Exception:
            pass

    # try resizing with Pillow if available
    try:
        from PIL import Image
        im = Image.open(file_path)
        max_dim = 512
        if max(im.size) > max_dim:
            im.thumbnail((max_dim, max_dim))
            im.save(file_path)
    except Exception:
        pass

    user.profile_picture = f"/uploads/avatars/{safe_name}"
    db.commit()
    return {"status": "success", "avatar_url": user.profile_picture}


# ==========================================
# 2. إدارة الموظفين (Administrators Only)
# ==========================================

@router.get("/roles", response_model=List[RoleResponse])
def get_available_roles(db: Session = Depends(get_db)):
    """جلب الرتب لملء القوائم المنسدلة (Dropdowns)"""
    return db.query(Role).filter(Role.role_name != "Owner").all()

@router.get("/", response_model=List[UserResponse])
def list_all_users(
    db: Session = Depends(get_db), 
    current_user: dict = Depends(role_required(["Admin", "Owner"])),
    _tenant_access: dict = Depends(require_tenant_isolation),
):
    """List users belonging to the authenticated customer's tenant."""
    tenant_id = current_user["customer_profile_id"]
    tenant_users = tenant_member_user_ids(db, tenant_id)
    users = (
        db.query(User)
        .outerjoin(Role, User.role_id == Role.role_id)
        .options(joinedload(User.role))
        .filter(or_(Role.role_name.is_(None), Role.role_name != "Owner"))
        .filter(User.user_id.in_(tenant_users))
        .all()
    )
    
    # تحسين: جلب كل أسماء المنشئين في طلب واحد لتقليل الضغط
    creator_ids = {u.created_by for u in users if u.created_by}
    creators = db.query(User).filter(User.user_id.in_(creator_ids)).all()
    creator_map = {c.user_id: c.full_name for c in creators}

    for u in users:
        u.creator_name = creator_map.get(u.created_by, "System")
        
    return [UserResponse.from_orm(u).dict() for u in users]

@router.post("/", response_model=UserResponse)
def authorize_new_user(
    payload: UserCreate, 
    db: Session = Depends(get_db), 
    current_user: dict = Depends(role_required(["Admin", "Owner"])),
    _tenant_access: dict = Depends(require_tenant_isolation),
):
    """Add an Officer to the authenticated customer's tenant."""
    if db.query(User).filter(or_(User.username == payload.username, User.email == payload.email)).first():
        raise HTTPException(status_code=400, detail="Username or Email already registered")

    role = db.query(Role).filter(Role.role_id == payload.role_id).first()
    if role is None or role.role_name != "Officer":
        raise HTTPException(
            status_code=403,
            detail="Customer administrators may create Officer accounts only",
        )

    customer_profile_id = current_user.get("customer_profile_id")
    if current_user.get("role") == "Owner":
        customer_profile_id = payload.customer_profile_id
        if customer_profile_id is None or not db.query(
            CustomerProfile.customer_profile_id
        ).filter(
            CustomerProfile.customer_profile_id == customer_profile_id
        ).first():
            raise HTTPException(
                status_code=404,
                detail="Customer profile not found",
            )

    new_user = User(
        full_name=payload.full_name,
        username=payload.username,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role_id=payload.role_id,
        phone=payload.phone,
        organization=payload.organization,
        created_by=current_user['user_id'],
        status="Active",
        customer_profile_id=customer_profile_id,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return UserResponse.from_orm(new_user).dict()

@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
def revoke_user_access(
    user_id: str, 
    db: Session = Depends(get_db), 
    current_user: dict = Depends(role_required(["Admin", "Owner"])),
    _tenant_access: dict = Depends(require_tenant_isolation),
):
    """Revoke an Officer account belonging to the authenticated tenant."""
    query = (
        db.query(User)
        .join(Role, User.role_id == Role.role_id)
        .filter(User.user_id == user_id, Role.role_name == "Officer")
    )
    if current_user.get("role") != "Owner":
        query = query.filter(
            User.customer_profile_id == current_user["customer_profile_id"]
        )
    user = query.first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.delete(user)
    db.commit()
    try:
        act = ActivityRepository(db)
        act.log(str(current_user.get("user_id")), "user_revoked", {"target": user_id})
    except Exception:
        pass
    return {"status": "success", "message": "User access revoked"}


@router.get("/profile/activity")
def my_activity(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_profile_access),
):
    repo = ActivityRepository(db)
    return repo.get_recent_for(current_user.get("user_id"))


@router.get("/profile/sessions")
def my_sessions(db: Session = Depends(get_db), current_user: dict = Depends(get_self_service_user)):
    tokens = db.query(RefreshToken).filter(RefreshToken.user_id == current_user.get("user_id")).all()
    return [
        {
            "session_id": str(t.id),
            "expires_at": t.expires_at,
            "revoked": t.revoked,
            "created_at": t.created_at,
            "user_agent": t.user_agent,
            "operating_system": t.operating_system,
            "browser": t.browser,
            "device_category": t.device_category,
            "device_type": t.device_type,
            "device_model": t.device_model,
        }
        for t in tokens
    ]


@router.post("/profile/logout-all")
def logout_all(db: Session = Depends(get_db), current_user: dict = Depends(get_self_service_user)):
    tokens = db.query(RefreshToken).filter(RefreshToken.user_id == current_user.get("user_id")).all()
    for t in tokens:
        t.revoked = True
    db.commit()
    try:
        act = ActivityRepository(db)
        act.log(str(current_user.get("user_id")), "logout_all", {})
    except Exception:
        pass
    return {"status": "success"}



@router.post("/profile/change-email")
def request_email_change(payload: dict, db: Session = Depends(get_db), current_user: dict = Depends(get_self_service_user)):
    new_email = payload.get("new_email")
    if not new_email:
        raise HTTPException(status_code=400, detail="new_email required")
    if db.query(User).filter(User.email == new_email).first():
        raise HTTPException(status_code=400, detail="Email already in use")
    token_repo = TokenRepository(db)
    token_str = create_refresh_token_string(40)
    expires_at = datetime.utcnow() + timedelta(hours=24)
    ev = EmailVerificationToken(user_id=current_user.get("user_id"), token=token_str, expires_at=expires_at, new_email=new_email)
    token_repo.create_email_verification(ev)
    try:
        send_verification_email(new_email, "", token_str)
    except Exception:
        pass
    try:
        act = ActivityRepository(db)
        act.log(str(current_user.get("user_id")), "email_change_requested", {"new_email": new_email})
    except Exception:
        pass
    return {"status": "verification_sent"}