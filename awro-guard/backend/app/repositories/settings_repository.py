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