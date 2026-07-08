from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func  # التصحيح: استيراد func من sqlalchemy مباشرة
from ...database.session import get_db
from ...models.models import User, Role
from ...schemas.schemas import UserRegister, UserLogin
from ...core.security import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])

# 1. مسار تسجيل حساب جديد (Section 1)
@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, db: Session = Depends(get_db)):
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
        status="Active"
    )
    db.add(new_user)
    db.commit()
    return {"status": "success", "message": "User registered successfully"}

# 2. مسار تسجيل الدخول (Section 1)
@router.post("/login")
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    # تحديث وقت آخر دخول (Section 3)
    user.last_login = func.now()
    db.commit()

    # إنشاء التوكن (JWT)
    token = create_access_token(data={
        "user_id": str(user.user_id),
        "role": user.role.role_name,
        "username": user.username
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "user_id": user.user_id,
            "full_name": user.full_name,
            "username": user.username,
            "role": user.role.role_name
        }
    }

# 3. مسار الخروج (Logout) - يتم التعامل معه في الفرونتيند بمسح التوكن
@router.post("/logout")
def logout():
    return {"status": "success", "message": "Logged out successfully"}


@router.get("/create-admin")
def create_admin(db: Session = Depends(get_db)):

    users = db.query(User).all()

    return {
        "count": len(users),
        "users": [u.username for u in users]
    }