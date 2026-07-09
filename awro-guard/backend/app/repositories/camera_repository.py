from sqlalchemy.orm import Session
from ..models.models import Camera

class CameraRepository:
    def __init__(self, db: Session):
        self.db = db

    def add_camera(self, camera_data: Camera, owner_id=None):
        if owner_id:
            camera_data.owner_id = owner_id
        self.db.add(camera_data)
        self.db.commit()
        self.db.refresh(camera_data)
        return camera_data

    def get_all_cameras(self, owner_id=None, is_admin: bool = False):
        query = self.db.query(Camera)
        if not is_admin and owner_id:
            query = query.filter(Camera.owner_id == owner_id)
        return query.all()