from __future__ import annotations

from typing import Callable

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from ..database.session import get_db
from ..models.models import (
    Camera,
    CustomerFeaturePermission,
    CustomerProfile,
    User,
)
from ..schemas.schemas import OwnerFeatureOption
from .auth_middleware import get_resource_user
from .tenant import customer_profile_for_user, tenant_camera_ids


FEATURE_OPTIONS = (
    OwnerFeatureOption(feature_key="dashboard", label="Dashboard"),
    OwnerFeatureOption(feature_key="cameras", label="Cameras"),
    OwnerFeatureOption(feature_key="analytics", label="Analytics and reports"),
    OwnerFeatureOption(feature_key="alerts", label="Alerts"),
    OwnerFeatureOption(feature_key="profile", label="Profile"),
    OwnerFeatureOption(feature_key="settings", label="Settings"),
)
FEATURE_KEYS = {option.feature_key for option in FEATURE_OPTIONS}

def has_customer_feature(db: Session, user_id: str, role: str | None, key: str) -> bool:
    if key not in FEATURE_KEYS:
        raise ValueError(f"Unknown customer feature: {key}")
    if role == "Owner":
        return True
    user = (
        db.query(User)
        .filter(User.user_id == user_id)
        .first()
    )
    profile = customer_profile_for_user(user) if user is not None else None
    if profile is None:
        return False
    if (
        profile.account_status != "ACTIVE"
        or profile.workflow_status != "PLATFORM_CUSTOMER"
    ):
        return False
    if profile.all_features:
        return True

    permission = (
        db.query(CustomerFeaturePermission)
        .filter(
            CustomerFeaturePermission.customer_profile_id
            == profile.customer_profile_id,
            CustomerFeaturePermission.feature_key == key,
        )
        .first()
    )
    return bool(permission and permission.is_allowed)


def require_customer_feature(key: str) -> Callable:
    if key not in FEATURE_KEYS:
        raise ValueError(f"Unknown customer feature: {key}")

    def check_feature(
        db: Session = Depends(get_db),
        current_user: dict = Depends(get_resource_user),
    ) -> dict:
        if not has_customer_feature(
            db, str(current_user["user_id"]), current_user.get("role"), key
        ):
            raise HTTPException(
                status_code=403,
                detail=f"The {key} feature is not enabled for this customer",
            )
        return current_user

    return check_feature


def require_any_customer_feature(*keys: str) -> Callable:
    if not keys or any(key not in FEATURE_KEYS for key in keys):
        raise ValueError("At least one valid customer feature is required")

    def check_features(
        db: Session = Depends(get_db),
        current_user: dict = Depends(get_resource_user),
    ) -> dict:
        user_id = str(current_user["user_id"])
        role = current_user.get("role")
        if not any(
            has_customer_feature(db, user_id, role, key) for key in keys
        ):
            feature_names = " or ".join(keys)
            raise HTTPException(
                status_code=403,
                detail=f"The {feature_names} feature is not enabled for this customer",
            )
        return current_user

    return check_features


def _check_camera_quota(
    db: Session, user_id: str, profile: CustomerProfile | None
) -> None:
    if profile is None:
        raise HTTPException(
            status_code=403,
            detail="Customer membership is not configured",
        )
    if profile.max_camera_count is None:
        return

    camera_count = (
        db.query(Camera)
        .filter(
            Camera.camera_id.in_(
                tenant_camera_ids(db, profile.customer_profile_id)
            )
        )
        .count()
    )
    if camera_count >= profile.max_camera_count:
        raise HTTPException(
            status_code=403,
            detail="The customer camera quota has been reached",
        )


def check_camera_quota(db: Session, user_id: str) -> None:
    user = db.query(User).filter(User.user_id == user_id).first()
    profile = customer_profile_for_user(user) if user is not None else None
    _check_camera_quota(db, user_id, profile)


def enforce_camera_quota(db: Session, user_id: str) -> None:
    user = db.query(User).filter(User.user_id == user_id).first()
    profile = customer_profile_for_user(user) if user is not None else None
    if profile is None:
        raise HTTPException(
            status_code=403,
            detail="Customer membership is not configured",
        )
    profile = (
        db.query(CustomerProfile)
        .filter(
            CustomerProfile.customer_profile_id
            == profile.customer_profile_id
        )
        .with_for_update()
        .first()
    )
    _check_camera_quota(db, user_id, profile)


def enforce_customer_camera_quota(db: Session, customer_profile_id: str) -> None:
    profile = (
        db.query(CustomerProfile)
        .filter(CustomerProfile.customer_profile_id == customer_profile_id)
        .with_for_update()
        .first()
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="Customer profile not found")
    _check_camera_quota(db, "", profile)


def enabled_customer_features(db: Session, user_id: str, role: str | None) -> list[str]:
    if role == "Owner":
        return [option.feature_key for option in FEATURE_OPTIONS]
    user = db.query(User).filter(User.user_id == user_id).first()
    profile = customer_profile_for_user(user) if user is not None else None
    if profile is None or (
        profile.account_status != "ACTIVE"
        or profile.workflow_status != "PLATFORM_CUSTOMER"
    ):
        return []
    if profile.all_features:
        return [option.feature_key for option in FEATURE_OPTIONS]

    allowed = {
        permission.feature_key
        for permission in db.query(CustomerFeaturePermission)
        .filter(
            CustomerFeaturePermission.customer_profile_id
            == profile.customer_profile_id,
            CustomerFeaturePermission.is_allowed.is_(True),
            CustomerFeaturePermission.feature_key.in_(FEATURE_KEYS),
        )
        .all()
    }
    return [
        option.feature_key
        for option in FEATURE_OPTIONS
        if option.feature_key in allowed
    ]
