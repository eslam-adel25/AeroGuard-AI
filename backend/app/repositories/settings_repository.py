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
        if s is None:
            return self.create_defaults_for(owner_id)

        preserved_abandoned_bag_seconds = s.abandoned_bag_seconds
        excluded_fields = {
            "settings_id",
            "owner_id",
            "created_at",
            "updated_at",
            "abandoned_bag_seconds",
        }
        for column in UserSettings.__table__.columns:
            if column.name in excluded_fields:
                continue
            default = column.default.arg if column.default is not None else None
            if callable(default):
                default = default()
            setattr(s, column.name, default)
        s.abandoned_bag_seconds = preserved_abandoned_bag_seconds
        self.db.commit()
        self.db.refresh(s)
        return s