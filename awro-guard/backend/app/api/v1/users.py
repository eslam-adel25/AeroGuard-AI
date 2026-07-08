import os
import uuid
import shutil
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_

from ...database.session import get_db
from ...models.models import User, Role
from ...schemas.schemas import (
    UserResponse,
    UserCreate,
    RoleResponse,
    UserProfileUpdate,
    PasswordChangeRequest,
)
from ...core.auth_middleware import get_current_user, role_required
from ...core.security import hash_password, verify_password

router = APIRouter(prefix="/users", tags=["Users & Profile"])

# المجلد الخاص بصور الملف الشخصي
UPLOAD_DIR = "uploads/avatars"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# ==========================================
# 1. مسارات الملف الشخصي (User Profile - Self)
# ==========================================

@router.get("/profile", response_model=UserResponse)
async def get_my_profile(
    db: Session = Depends(get_db), 
    current_user: dict = Depends(get_current_user)
):
    """جلب بيانات الموظف المسجل حالياً (صاحب التوكن)"""
    user = db.query(User).options(joinedload(User.role)).filter(User.user_id == current_user['user_id']).first()
    if not user:
        raise HTTPException(status_code=404, detail="User profile not found")
    return user

@router.put("/profile", response_model=UserResponse)
async def update_my_profile(
    payload: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """تعديل الموظف لبياناته الشخصية (الاسم، الإيميل، الهاتف)"""
    user = db.query(User).filter(User.user_id == current_user['user_id']).first()

    if payload.email and payload.email != user.email:
        # التأكد من عدم تكرار الإيميل الجديد
        if db.query(User).filter(User.email == payload.email).first():
            raise HTTPException(status_code=400, detail="Email already in use")
        user.email = payload.email

    if payload.full_name:
        user.full_name = payload.full_name
    if payload.phone:
        user.phone = payload.phone
    if payload.organization is not None:
        user.organization = payload.organization
    
    db.commit()
    db.refresh(user)
    return user

@router.put("/profile/password")
@router.post("/profile/password")
async def change_my_password(
    payload: PasswordChangeRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """تغيير كلمة المرور بعد التحقق من القديمة (Section 3)"""
    user = db.query(User).filter(User.user_id == current_user['user_id']).first()

    if not verify_password(payload.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password incorrect")

    user.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"status": "success", "message": "Password updated successfully"}

@router.post("/profile/avatar")
async def upload_my_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """رفع صورة شخصية (Avatar) وحفظ المسار (Section 3)"""
    user = db.query(User).filter(User.user_id == current_user['user_id']).first()
    
    # تأمين اسم الملف وحفظه
    file_ext = file.filename.split(".")[-1]
    file_name = f"{user.user_id}_{uuid.uuid4().hex[:8]}.{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, file_name)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # تحديث مسار الصورة في قاعدة البيانات
    user.profile_picture = file_path
    db.commit()
    return {"status": "success", "avatar_url": file_path}


# ==========================================
# 2. إدارة الموظفين (Administrators Only)
# ==========================================

@router.get("/roles", response_model=List[RoleResponse])
def get_available_roles(db: Session = Depends(get_db)):
    """جلب الرتب لملء القوائم المنسدلة (Dropdowns)"""
    return db.query(Role).all()

@router.get("/", response_model=List[UserResponse])
def list_all_users(
    db: Session = Depends(get_db), 
    current_user: dict = Depends(role_required(["Administrator"]))
):
    """جلب كافة الموظفين مع أسماء من قاموا بإضافتهم (Admins Only)"""
    users = db.query(User).options(joinedload(User.role)).all()
    
    # تحسين: جلب كل أسماء المنشئين في طلب واحد لتقليل الضغط
    creator_ids = {u.created_by for u in users if u.created_by}
    creators = db.query(User).filter(User.user_id.in_(creator_ids)).all()
    creator_map = {c.user_id: c.full_name for c in creators}

    for u in users:
        u.creator_name = creator_map.get(u.created_by, "System")
        
    return users

@router.post("/", response_model=UserResponse)
def authorize_new_user(
    payload: UserCreate, 
    db: Session = Depends(get_db), 
    current_user: dict = Depends(role_required(["Administrator"]))
):
    """إضافة موظف جديد بواسطة الأدمن (Section 1)"""
    if db.query(User).filter(or_(User.username == payload.username, User.email == payload.email)).first():
        raise HTTPException(status_code=400, detail="Username or Email already registered")

    new_user = User(
        full_name=payload.full_name,
        username=payload.username,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role_id=payload.role_id,
        phone=payload.phone,
        organization=payload.organization,
        created_by=current_user['user_id'],
        status="Active"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
def revoke_user_access(
    user_id: str, 
    db: Session = Depends(get_db), 
    current_user: dict = Depends(role_required(["Administrator"]))
):
    """حذف موظف نهائياً (Section 3)"""
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.delete(user)
    db.commit()
    return {"status": "success", "message": "User access revoked"}