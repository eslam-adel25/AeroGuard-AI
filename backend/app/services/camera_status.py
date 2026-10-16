import time

from ..models.models import Camera


# Require recent frames, but tolerate brief stream delays for ten seconds.
CAMERA_NO_FRAME_GRACE_SECONDS = 10.0


def resolve_camera_status(camera_id, stored_status, runtime_states, now=None):
    camera_key = str(camera_id)
    runtime = runtime_states.get(camera_key)
    if runtime is None:
        if (stored_status or "").strip().lower() in {"processing", "running"}:
            return "Offline"
        return stored_status

    if runtime.get("stop_requested", False):
        return "Offline"

    current_time = time.monotonic() if now is None else now
    last_frame_at = runtime["last_frame_at"]
    if last_frame_at is not None:
        if current_time - last_frame_at <= CAMERA_NO_FRAME_GRACE_SECONDS:
            return "Running"
        return "Offline"

    if current_time - runtime["started_at"] <= CAMERA_NO_FRAME_GRACE_SECONDS:
        return "Processing"
    return "Offline"


def apply_camera_runtime_statuses(cameras, ai_engine):
    camera_ids = [
        str(camera.camera_id) if hasattr(camera, "camera_id") else str(camera["camera_id"])
        for camera in cameras
    ]
    runtime_states = (
        ai_engine.get_camera_runtime_statuses(camera_ids)
        if ai_engine is not None
        else {}
    )

    for camera in cameras:
        if hasattr(camera, "camera_id"):
            camera_id = str(camera.camera_id)
            stored_status = camera.status
            camera.status = resolve_camera_status(
                camera_id,
                stored_status,
                runtime_states,
            )
        else:
            camera_id = str(camera["camera_id"])
            camera["status"] = resolve_camera_status(
                camera_id,
                camera.get("status"),
                runtime_states,
            )


def reconcile_orphaned_processing_statuses(db):
    updated = db.query(Camera).filter(
        Camera.status == "Processing"
    ).update(
        {Camera.status: "Offline"},
        synchronize_session=False,
    )
    db.commit()
    return updated
