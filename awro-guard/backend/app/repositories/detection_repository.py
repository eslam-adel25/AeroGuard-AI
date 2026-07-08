from sqlalchemy.orm import Session
from ..models.models import Detection

class DetectionRepository:
    def __init__(self, db: Session):
        self.db = db

    def save_detection(self, detection: Detection):
        self.db.add(detection)
        self.db.commit()
        self.db.refresh(detection)
        return detection