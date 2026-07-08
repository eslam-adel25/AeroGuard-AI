from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ...database.session import get_db
from ...models.models import SystemSettings
from ...schemas.schemas import SettingsUpdate
from ...core.auth_middleware import role_required

router = APIRouter(prefix="/settings", tags=["Settings"])

@router.get("/")
def get_current_settings(db: Session = Depends(get_db)):
    # جلب السطر الأول والوحيد للإعدادات
    settings = db.query(SystemSettings).first()
    return settings

@router.put("/")
def update_settings(
    payload: SettingsUpdate, 
    db: Session = Depends(get_db), 
    current_user = Depends(role_required(["Administrator"]))
):
    settings = db.query(SystemSettings).first()
    if not settings:
        settings = SystemSettings()
        db.add(settings)
    
    # تحديث الحقول المُرسلة فقط لتفادي استبدال القيم الحالية بـ None
    for key, value in payload.model_dump(exclude_none=True).items():
        setattr(settings, key, value)
    
    db.commit()
    db.refresh(settings)
    
    # تحديث محرك الـ AI بالقيم الجديدة فوراً
    from ...ai.processor import ai_engine
    ai_engine.update_config(settings)
    
    return {"status": "success", "message": "Global settings updated"}