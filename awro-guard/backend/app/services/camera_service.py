from ..repositories.camera_repository import CameraRepository
from ..models.models import Camera

class CameraService:
    def __init__(self, camera_repo: CameraRepository):
        self.camera_repo = camera_repo

    def register_new_camera(self, camera_data):
        # هنا يمكن إضافة فحص للرابط (Ping) قبل الحفظ
        new_cam = Camera(**camera_data.dict())
        return self.camera_repo.add_camera(new_cam)

    def list_cameras(self):
        return self.camera_repo.get_all_cameras()