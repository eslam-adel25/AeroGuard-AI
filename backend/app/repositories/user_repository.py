from sqlalchemy.orm import Session, joinedload
from ..models.models import User, Role

class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_user_by_username(self, username: str):
        """البحث عن مستخدم معين مع جلب رتبته لضمان نجاح التوكن"""
        return self.db.query(User).options(joinedload(User.role)).filter(User.username == username).first()

    def get_user_by_email(self, email: str):
        return self.db.query(User).options(joinedload(User.role)).filter(User.email == email).first()

    def get_user_by_id(self, user_id: str):
        return self.db.query(User).options(joinedload(User.role)).filter(User.user_id == user_id).first()

    def get_all_users(self):
        """جلب كافة المستخدمين المسجلين لعرضهم في جدول الموظفين (صفحة 148)"""
        # استخدام joinedload يحل مشكلة الـ 422 لأنه يملأ حقل 'role' الذي ينتظره الفرونتيند
        return self.db.query(User).options(joinedload(User.role)).all()

    def create_user(self, user_model: User):
        """إضافة موظف أمن جديد للقاعدة"""
        self.db.add(user_model)
        self.db.commit()
        self.db.refresh(user_model)
        return user_model

    def update_user_status(self, user_id: str, new_status: str):
        """تحديث حالة المستخدم (Active/Inactive) - Soft Delete (صفحة 205)"""
        user = self.db.query(User).filter(User.user_id == user_id).first()
        if user:
            user.status = new_status
            self.db.commit()
            return True
        return False

    def mark_verified(self, user_id: str):
        user = self.db.query(User).filter(User.user_id == user_id).first()
        if user:
            user.is_verified = True
            user.status = "Active"
            self.db.commit()
            return True
        return False

    def set_last_login(self, user_id: str):
        user = self.db.query(User).filter(User.user_id == user_id).first()
        if user:
            from sqlalchemy import func
            user.last_login = func.now()
            self.db.commit()
            return True
        return False