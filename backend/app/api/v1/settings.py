from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ...database.session import get_db
from ...schemas.schemas import SettingsUpdate, SettingsResponse
from ...core.auth_middleware import get_resource_user, require_tenant_isolation
from ...core.customer_features import require_customer_feature
from ...repositories.settings_repository import SettingsRepository
from ...models.models import SystemSettings

router = APIRouter(
    prefix="/settings",
    tags=["Settings"],
    dependencies=[
        Depends(require_customer_feature("settings")),
        Depends(require_tenant_isolation),
    ],
)

# Global reference to AI processor (set during app initialization)
_ai_processor = None

def set_ai_processor(processor):
    """Called by main.py to register the AI processor instance"""
    global _ai_processor
    _ai_processor = processor


@router.get("/", response_model=SettingsResponse)
def get_current_settings(db: Session = Depends(get_db), current_user: dict = Depends(get_resource_user)):
    """Get current user settings from database"""
    repo = SettingsRepository(db)
    owner_id = current_user.get("user_id")
    settings = repo.get_by_owner(owner_id)
    if not settings:
        settings = repo.create_defaults_for(owner_id)
    return SettingsResponse.from_orm(settings).dict()


@router.put("/", response_model=SettingsResponse)
def update_settings(payload: SettingsUpdate, db: Session = Depends(get_db), current_user: dict = Depends(get_resource_user)):
    """Update user settings and reload AI processor"""
    repo = SettingsRepository(db)
    owner_id = current_user.get("user_id")
    settings_data = payload.dict(exclude_none=True)
    settings = repo.update(owner_id, settings_data)
    
    # Notify AI processor to reload settings
    if _ai_processor is not None:
        try:
            _ai_processor.update_config(
                settings, db.query(SystemSettings).first()
            )
            print(f"✅ AI Processor reloaded with new settings for user {owner_id}")
        except Exception as e:
            print(f"⚠️ Failed to reload AI processor: {e}")
    
    return SettingsResponse.from_orm(settings).dict()


@router.post("/reset", response_model=SettingsResponse)
def reset_settings(db: Session = Depends(get_db), current_user: dict = Depends(get_resource_user)):
    """Reset settings to defaults"""
    repo = SettingsRepository(db)
    owner_id = current_user.get("user_id")
    settings = repo.reset_to_defaults(owner_id)
    
    # Notify AI processor
    if _ai_processor is not None:
        try:
            _ai_processor.update_config(
                settings, db.query(SystemSettings).first()
            )
            print(f"✅ AI Processor reset to defaults for user {owner_id}")
        except Exception as e:
            print(f"⚠️ Failed to reload AI processor: {e}")
    
    return SettingsResponse.from_orm(settings).dict()