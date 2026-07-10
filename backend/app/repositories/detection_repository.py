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

    def get_detections(
        self,
        camera_id: str | None = None,
        owner_id: str | None = None,
        is_admin: bool = False,
        limit: int = 100,
        offset: int = 0,
    ):
        q = self.db.query(Detection)
        if camera_id:
            q = q.filter(Detection.camera_id == camera_id)
        if owner_id and not is_admin:
            q = q.filter(Detection.owner_id == owner_id)
        return q.order_by(Detection.detected_at.desc()).offset(offset).limit(limit).all()