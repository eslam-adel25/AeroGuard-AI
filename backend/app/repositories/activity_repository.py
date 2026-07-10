from sqlalchemy.orm import Session
from ..models.models import ActivityLog


class ActivityRepository:
    def __init__(self, db: Session):
        self.db = db

    def log(self, user_id: str, event_type: str, details: dict | None = None, ip: str | None = None, user_agent: str | None = None):
        a = ActivityLog(user_id=user_id, event_type=event_type, details=details or {}, ip_address=ip, user_agent=user_agent)
        self.db.add(a)
        self.db.commit()
        self.db.refresh(a)
        return a

    def get_recent_for(self, user_id: str, limit: int = 50):
        return self.db.query(ActivityLog).filter(ActivityLog.user_id == user_id).order_by(ActivityLog.created_at.desc()).limit(limit).all()

    def get_all(self, limit: int = 100):
        return self.db.query(ActivityLog).order_by(ActivityLog.created_at.desc()).limit(limit).all()
