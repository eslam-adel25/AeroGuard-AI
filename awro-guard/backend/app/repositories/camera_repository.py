from sqlalchemy.orm import Session
from ..models.models import Camera

class CameraRepository:
    def __init__(self, db: Session):
        self.db = db

    def add_camera(self, camera_data: Camera):
        self.db.add(camera_data)
        self.db.commit()
        self.db.refresh(camera_data)
        return camera_data

    def get_all_cameras(self):
        return self.db.query(Camera).all()