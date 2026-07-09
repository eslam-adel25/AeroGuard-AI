from sqlalchemy.orm import Session
from ..models.models import UserSettings


class SettingsRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_owner(self, owner_id: str):
        return self.db.query(UserSettings).filter(UserSettings.owner_id == owner_id).first()

    def create_defaults_for(self, owner_id: str):
        s = UserSettings(owner_id=owner_id)
        self.db.add(s)
        self.db.commit()
        self.db.refresh(s)
        return s

    def update(self, owner_id: str, payload: dict):
        s = self.get_by_owner(owner_id)
        if not s:
            s = UserSettings(owner_id=owner_id)
            self.db.add(s)
        for k, v in payload.items():
            if hasattr(s, k) and v is not None:
                setattr(s, k, v)
        self.db.commit()
        self.db.refresh(s)
        return s

    def reset_to_defaults(self, owner_id: str):
        s = self.get_by_owner(owner_id)
        if s:
            self.db.delete(s)
            self.db.commit()
        return self.create_defaults_for(owner_id)
from sqlalchemy.orm import Session
from ..models.models import Report # سنستخدم موديل الإعدادات إذا أضفته، أو سنقوم بتحديث الجدول مباشرة

class SettingsRepository:
    def __init__(self, db: Session):
        self.db = db

    def update_setting(self, key: str, value: str):
        # منطق تحديث الإعدادات في الداتا بيز (صفحة 207)
        # ملاحظة: سنقوم حالياً بتبسيطها لتخزين القيم في ملف .env أو متغيرات النظام
        # لضمان السرعة القصوى للـ AI
        import os
        os.environ[key] = str(value)
        return True