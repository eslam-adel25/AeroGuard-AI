from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ...core.auth_middleware import (
    ensure_platform_owner_active,
    ensure_user_can_access_platform,
    get_authenticated_user,
)
from ...core.customer_features import has_customer_feature
from ...core.tenant import tenant_camera_child_filter, tenant_owner_filter
from ...database.session import get_db
from ...models.models import AIEvent, Camera, User

router = APIRouter(tags=["Protected files"])
UPLOAD_ROOT = Path(__file__).resolve().parents[3] / "uploads"


def resolve_upload_file(relative_path: str) -> Path | None:
    root = UPLOAD_ROOT.resolve()
    try:
        candidate = (root / relative_path).resolve(strict=True)
        candidate.relative_to(root)
    except (OSError, ValueError):
        return None
    return candidate if candidate.is_file() else None


def _same_stored_path(stored_path: str | None, requested_path: Path) -> bool:
    if not stored_path:
        return False
    try:
        return Path(stored_path).resolve() == requested_path
    except (OSError, RuntimeError, ValueError):
        return False


def _deny_unknown_file() -> None:
    raise HTTPException(status_code=404, detail="File not found")


@router.get("/uploads/{file_path:path}")
def get_protected_upload(
    file_path: str,
    db: Session = Depends(get_db),
    identity: dict = Depends(get_authenticated_user),
):
    user: User = identity["_user"]
    role_name = user.role.role_name if user.role else None
    is_owner = role_name == "Owner"
    if is_owner:
        ensure_platform_owner_active(user)
    else:
        ensure_user_can_access_platform(user)

    normalized_relative = Path(file_path).as_posix()
    if normalized_relative.startswith("avatars/"):
        path = resolve_upload_file(file_path)
        if path is None:
            _deny_unknown_file()
        if not is_owner and not has_customer_feature(
            db, str(user.user_id), role_name, "profile"
        ):
            raise HTTPException(
                status_code=403,
                detail="The profile feature is not enabled for this customer",
            )
        avatar_url = f"/uploads/{normalized_relative}"
        owners = db.query(User).filter(User.profile_picture == avatar_url).all()
        if not owners:
            _deny_unknown_file()
        is_owner_avatar = any(
            owner.role and owner.role.role_name == "Owner" for owner in owners
        )
        owns_avatar = any(owner.user_id == user.user_id for owner in owners)
        if is_owner_avatar and not is_owner and not owns_avatar:
            raise HTTPException(status_code=403, detail="Forbidden")
        if not owns_avatar and not is_owner:
            raise HTTPException(status_code=403, detail="Forbidden")
        return FileResponse(path, headers={"Cache-Control": "private, no-store"})

    path = resolve_upload_file(file_path)
    if path is None:
        _deny_unknown_file()

    tenant_id = identity.get("customer_profile_id")
    if not is_owner and not tenant_id:
        raise HTTPException(
            status_code=403,
            detail="Customer membership is not configured",
        )

    if normalized_relative.startswith("ai_events/"):
        if not is_owner and not any(
            has_customer_feature(db, str(user.user_id), role_name, feature)
            for feature in ("alerts", "analytics")
        ):
            raise HTTPException(
                status_code=403,
                detail="The alerts or analytics feature is not enabled for this customer",
            )
        event_query = db.query(AIEvent).filter(
            AIEvent.screenshot_path == str(path)
        )
        if not is_owner:
            event_query = event_query.filter(
                tenant_camera_child_filter(
                    AIEvent,
                    db,
                    tenant_id,
                    actor_column=AIEvent.detected_by,
                )
            )
        events = event_query.all()
        if not events:
            _deny_unknown_file()
        camera_ids = {event.camera_id for event in events if event.camera_id}
        cameras = (
            db.query(Camera)
            .filter(Camera.camera_id.in_(camera_ids))
            .all()
            if camera_ids
            else []
        )
        return FileResponse(path, headers={"Cache-Control": "private, no-store"})

    if normalized_relative.startswith("videos/"):
        if not is_owner and not has_customer_feature(
            db, str(user.user_id), role_name, "cameras"
        ):
            raise HTTPException(
                status_code=403,
                detail="The cameras feature is not enabled for this customer",
            )
        camera_query = db.query(Camera).filter(Camera.camera_type == "UPLOAD")
        if not is_owner:
            camera_query = camera_query.filter(
                tenant_owner_filter(
                    Camera,
                    db,
                    tenant_id,
                    Camera.owner_id,
                )
            )
        cameras = camera_query.all()
        matching_cameras = [
            camera
            for camera in cameras
            if _same_stored_path(camera.stream_url, path)
        ]
        if not matching_cameras:
            _deny_unknown_file()
        return FileResponse(path, headers={"Cache-Control": "private, no-store"})

    # Report exports are served by owner-checked /reports/export endpoints.
    # Their generated files are not linked to report rows by a persistent path.
    _deny_unknown_file()
