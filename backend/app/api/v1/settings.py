from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ...database.session import get_db
from ...schemas.schemas import SettingsUpdate, SettingsResponse
from ...core.auth_middleware import get_current_user
from ...repositories.settings_repository import SettingsRepository

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("/", response_model=SettingsResponse)
def get_current_settings(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    repo = SettingsRepository(db)
    owner_id = current_user.get("user_id")
    settings = repo.get_by_owner(owner_id)
    if not settings:
        settings = repo.create_defaults_for(owner_id)
    return SettingsResponse.model_validate(settings).model_dump()


@router.put("/", response_model=SettingsResponse)
def update_settings(payload: SettingsUpdate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    repo = SettingsRepository(db)
    owner_id = current_user.get("user_id")
    settings = repo.update(owner_id, payload.model_dump(exclude_none=True))
    return SettingsResponse.model_validate(settings).model_dump()


@router.post("/reset", response_model=SettingsResponse)
def reset_settings(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    repo = SettingsRepository(db)
    owner_id = current_user.get("user_id")
    settings = repo.reset_to_defaults(owner_id)
    return SettingsResponse.model_validate(settings).model_dump()