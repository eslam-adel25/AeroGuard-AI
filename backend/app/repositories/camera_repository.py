from sqlalchemy.orm import Session
from fastapi import HTTPException
from ..core.customer_features import enforce_camera_quota
from ..models.models import Camera, CustomerProfile, User
from ..core.tenant import tenant_owner_filter
from ..core.tenant import customer_profile_for_user


class CameraRepository:
    def __init__(self, db: Session):
        self.db = db

    def add_camera(
        self,
        camera_data: Camera,
        owner_id=None,
        customer_profile_id=None,
        platform_owner: bool = False,
    ):
        if owner_id:
            camera_data.owner_id = owner_id
        owner = (
            self.db.query(User)
            .filter(User.user_id == camera_data.owner_id)
            .first()
            if camera_data.owner_id
            else None
        )
        if platform_owner:
            if not customer_profile_id:
                raise HTTPException(
                    status_code=422,
                    detail="A customer profile is required to create a camera",
                )
            profile = (
                self.db.query(CustomerProfile)
                .filter(
                    CustomerProfile.customer_profile_id == customer_profile_id
                )
                .first()
            )
        else:
            profile = customer_profile_for_user(owner) if owner else None
        if profile is None or (
            not platform_owner
            and customer_profile_id is not None
            and str(customer_profile_id) != str(profile.customer_profile_id)
        ):
            raise HTTPException(
                status_code=403,
                detail="Customer membership is not configured",
            )
        camera_data.customer_profile_id = profile.customer_profile_id
        if platform_owner:
            from ..core.customer_features import enforce_customer_camera_quota

            enforce_customer_camera_quota(
                self.db, str(profile.customer_profile_id)
            )
        elif camera_data.owner_id:
            enforce_camera_quota(self.db, str(camera_data.owner_id))
        try:
            self.db.add(camera_data)
            self.db.commit()
            self.db.refresh(camera_data)
        except Exception:
            self.db.rollback()
            raise
        return camera_data

    def get_all_cameras(
        self,
        owner_id=None,
        is_admin: bool = False,
        customer_profile_id=None,
        platform_wide: bool = False,
    ):
        query = self.db.query(Camera)
        if platform_wide:
            return query.all()
        if customer_profile_id:
            query = query.filter(
                tenant_owner_filter(
                    Camera,
                    self.db,
                    customer_profile_id,
                    Camera.owner_id,
                )
            )
        elif not is_admin and owner_id:
            query = query.filter(Camera.owner_id == owner_id)
        elif is_admin:
            query = query.filter(False)
        return query.all()

    def get_camera_for_user(
        self,
        camera_id,
        user_id=None,
        is_admin: bool = False,
        customer_profile_id=None,
        platform_wide: bool = False,
    ):
        query = self.db.query(Camera).filter(Camera.camera_id == camera_id)
        if platform_wide:
            return query.first()
        if customer_profile_id:
            query = query.filter(
                tenant_owner_filter(
                    Camera,
                    self.db,
                    customer_profile_id,
                    Camera.owner_id,
                )
            )
        elif not is_admin and user_id:
            query = query.filter(Camera.owner_id == user_id)
        elif is_admin:
            query = query.filter(False)
        return query.first()