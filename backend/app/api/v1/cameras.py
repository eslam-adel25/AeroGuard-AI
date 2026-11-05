import os
import logging
import shutil
import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session
import cv2
import asyncio
from urllib.parse import unquote_plus, urlparse, urlsplit, urlunsplit

from ...database.session import get_db
from ...ai.capture import (
    CameraSourceError,
    RTSPCaptureError,
    RTSP_TIMEOUT_SECONDS,
    open_live_capture,
    resolve_camera_source,
)
from ...models.models import (
    Camera,
    CustomerProfile,
    RestrictedZone,
    AIEvent,
    Detection,
    Tracking,
)
from ...schemas.schemas import (
    CameraResponse,
    TripwireOccupancyConfirmation,
    ZoneCreate,
    ZoneResponse,
)
from ...core.auth_middleware import (
    get_resource_user,
    require_tenant_isolation,
)
from ...core.customer_features import (
    check_camera_quota,
    enforce_customer_camera_quota,
    require_customer_feature,
)
from ...core.tenant import tenant_camera_child_filter, tenant_owner_filter
from ...repositories.camera_repository import CameraRepository
from ...services.camera_status import (
    apply_camera_runtime_statuses,
    resolve_camera_status,
)
from ...services.go2rtc import (
    Go2RTCError,
    build_go2rtc_source_url,
    go2rtc_service,
    resolve_live_pipeline_url,
)
from ...ai.processor import ai_engine 
from ...websocket.manager import manager

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/cameras",
    tags=["Cameras"],
    dependencies=[
        Depends(require_customer_feature("cameras")),
        Depends(require_tenant_isolation),
    ],
)


def _get_camera_for_user(db: Session, camera_id: str, current_user: dict):
    tenant_id = current_user.get("customer_profile_id")
    if not tenant_id:
        raise HTTPException(status_code=403, detail="Customer membership is not configured")
    cam = (
        db.query(Camera)
        .filter(
            Camera.camera_id == camera_id,
            tenant_owner_filter(
                Camera,
                db,
                tenant_id,
                Camera.owner_id,
            ),
        )
        .first()
    )
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    return cam

# المجلد الجذري لوحدة backend
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
UPLOAD_DIR = Path(BASE_DIR) / "uploads" / "videos"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_VIDEO_EXTENSIONS = {"mp4", "mov", "avi", "mkv", "webm"}
MAX_VIDEO_SIZE = 200 * 1024 * 1024
LIVE_PROBE_TIMEOUT_SECONDS = RTSP_TIMEOUT_SECONDS
RTSP_CAMERA_TYPES = {"LIVE", "NVR"}


def _validate_live_rtsp_url(stream_url: str) -> str:
    value = (stream_url or "").strip()
    parsed = urlparse(value)
    if parsed.scheme not in {"rtsp", "rtsps"} or not parsed.netloc:
        raise HTTPException(status_code=400, detail="A valid RTSP URL is required")
    return value


def _redact_stream_url_credentials(stream_url: str) -> str:
    parts = urlsplit(stream_url)
    host = parts.netloc.rsplit("@", 1)[-1]
    sensitive_query_keys = {
        "access_key",
        "access_token",
        "api_key",
        "auth",
        "authorization",
        "credential",
        "password",
        "passwd",
        "pwd",
        "secret",
        "token",
        "user",
        "username",
    }
    query = []
    for pair in parts.query.split("&"):
        key, separator, _ = pair.partition("=")
        if unquote_plus(key).lower() in sensitive_query_keys:
            query.append(f"{key}{separator}REDACTED")
        else:
            query.append(pair)
    return urlunsplit(
        (parts.scheme, host, parts.path, "&".join(query), parts.fragment)
    )


def _camera_response(camera: Camera) -> CameraResponse:
    response = CameraResponse.from_orm(camera)
    response.stream_url = _redact_stream_url_credentials(response.stream_url)
    return response


def resolve_camera_live_source(camera_id: str, stream_url: str | None = None) -> str | None:
    go2rtc_url = resolve_live_pipeline_url(camera_id, stream_url)
    if go2rtc_url is not None:
        return go2rtc_url
    if stream_url:
        return stream_url
    return None


def resolve_camera_restream_url(camera_id: str, stream_url: str | None = None) -> str | None:
    source_url = stream_url or ""
    if not source_url:
        return None
    return build_go2rtc_source_url(camera_id, source_url)


def _encode_mjpeg_frame(frame) -> bytes | None:
    if (
        frame is None
        or getattr(frame, "size", 0) <= 0
        or len(getattr(frame, "shape", ())) != 3
    ):
        return None
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            "camera frame stage=pre-encode shape=%s dtype=%s contiguous=%s",
            getattr(frame, "shape", None),
            getattr(getattr(frame, "dtype", None), "name", None),
            bool(getattr(frame, "flags", {}).c_contiguous)
            if getattr(frame, "flags", None) is not None
            else None,
        )
    encoded, buffer = cv2.imencode(
        ".jpg",
        frame,
        [int(cv2.IMWRITE_JPEG_QUALITY), 75],
    )
    if not encoded or buffer is None or buffer.size <= 0:
        return None
    payload = buffer.tobytes()
    if not payload.startswith(b"\xff\xd8") or not payload.endswith(b"\xff\xd9"):
        return None
    return payload


def _probe_live_rtsp(stream_url: str) -> bool:
    capture = cv2.VideoCapture()
    try:
        if not open_live_capture(
            capture,
            stream_url,
            timeout_seconds=LIVE_PROBE_TIMEOUT_SECONDS,
        ) or not capture.isOpened():
            raise RTSPCaptureError("open_failed")
        ret, frame = capture.read()
        if not ret or frame is None or frame.size <= 0:
            raise RTSPCaptureError("no_frame")
        return True
    finally:
        capture.release()


async def _verify_live_rtsp(stream_url: str) -> None:
    try:
        available = await asyncio.wait_for(
            asyncio.to_thread(_probe_live_rtsp, stream_url),
            timeout=LIVE_PROBE_TIMEOUT_SECONDS + 1,
        )
    except asyncio.TimeoutError:
        logger.warning("RTSP probe failed: connection_timeout")
        detail = "RTSP connection timed out"
    except RTSPCaptureError as exc:
        logger.warning("RTSP probe failed: %s", exc.category)
        detail = {
            "connection_timeout": "RTSP connection timed out",
            "authentication_rejected": "RTSP server rejected authentication (401)",
            "authorization_rejected": "RTSP server rejected authorization (403)",
            "backend_unavailable": "RTSP capture backend or timeout configuration is unavailable",
            "no_frame": "RTSP stream opened but no frame was received",
            "open_failed": "RTSP connection failed; server response is unavailable",
        }.get(exc.category, "RTSP connection failed")
    except Exception as exc:
        logger.warning("RTSP probe failed unexpectedly: %s", type(exc).__name__)
        detail = "RTSP probe failed unexpectedly"
    else:
        if available:
            return
        detail = "RTSP connection failed; server response is unavailable"

    if detail:
        raise HTTPException(
            status_code=400,
            detail=detail,
        )


async def _run_live_camera(
    camera_id: str,
    stream_url: str,
    reserved: bool = False,
    camera_type: str = "LIVE",
) -> None:
    await ai_engine.process_camera(
        camera_id,
        stream_url,
        reserved=reserved,
        camera_type=camera_type,
    )

# 1. تسجيل كاميرا (بث مباشر أو رفع فيديو)
@router.post("/", response_model=CameraResponse)
async def add_camera(
    camera_name: str = Form(...),
    location: str = Form(...),
    camera_type: str = Form(...), # LIVE or UPLOAD
    stream_url: str = Form(None), # لروابط RTSP/IP
    video_file: UploadFile = File(None), # لرفع ملفات الفيديو
    customer_profile_id: uuid.UUID | None = Form(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_resource_user)
):
    is_platform_owner = current_user.get("role") == "Owner"
    if is_platform_owner:
        if not customer_profile_id:
            raise HTTPException(
                status_code=422,
                detail="A customer profile is required to create a camera",
            )
        profile_exists = (
            db.query(CustomerProfile.customer_profile_id)
            .filter(
                CustomerProfile.customer_profile_id == customer_profile_id
            )
            .first()
        )
        if not profile_exists:
            raise HTTPException(status_code=404, detail="Customer profile not found")
        enforce_customer_camera_quota(db, customer_profile_id)
    else:
        customer_profile_id = current_user.get("customer_profile_id")
        check_camera_quota(db, str(current_user.get("user_id")))
    camera_type = camera_type.strip().upper()
    final_url = stream_url
    if camera_type in RTSP_CAMERA_TYPES:
        final_url = _validate_live_rtsp_url(stream_url)
        try:
            go2rtc_service.start()
        except Go2RTCError as exc:
            raise HTTPException(
                status_code=503,
                detail="go2rtc live streaming service is unavailable",
            ) from exc
        await _verify_live_rtsp(final_url)
    elif camera_type == "USB":
        final_url = "0"

    uploaded_file_path = None
    if camera_type == "UPLOAD" and video_file:
        if not video_file.filename:
            raise HTTPException(status_code=400, detail="Invalid file name")
        file_name = Path(video_file.filename).name
        file_ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
        if file_ext not in ALLOWED_VIDEO_EXTENSIONS:
            raise HTTPException(status_code=400, detail="Invalid file type")
        contents = await video_file.read()
        if len(contents) > MAX_VIDEO_SIZE:
            raise HTTPException(status_code=400, detail="File too large")
        safe_name = f"{uuid.uuid4().hex}.{file_ext}"
        uploaded_file_path = UPLOAD_DIR / safe_name
        with uploaded_file_path.open("wb") as buffer:
            buffer.write(contents)
        final_url = str(uploaded_file_path)
    elif camera_type == "UPLOAD":
        try:
            resolve_camera_source(camera_type, final_url)
        except CameraSourceError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    elif camera_type not in {"USB"}:
        raise HTTPException(status_code=422, detail="Unsupported camera source type")

    new_cam = Camera(
        camera_name=camera_name,
        location=location,
        stream_url=final_url,
        camera_type=camera_type,
        status="Online" if camera_type in ["UPLOAD", "USB"] else "Offline"
    )
    repo = CameraRepository(db)
    try:
        created = repo.add_camera(
            new_cam,
            owner_id=current_user.get("user_id"),
            customer_profile_id=customer_profile_id,
            platform_owner=is_platform_owner,
        )
    except Exception:
        if uploaded_file_path is not None:
            try:
                uploaded_file_path.unlink()
            except FileNotFoundError:
                pass
            except OSError:
                logger.exception("Could not remove video upload after camera creation failed")
        raise
    if camera_type in RTSP_CAMERA_TYPES:
        try:
            go2rtc_service.register_stream(created.camera_id, final_url)
        except Go2RTCError as exc:
            db.delete(created)
            db.commit()
            raise HTTPException(
                status_code=503,
                detail="Camera was not saved because its go2rtc stream could not be registered",
            ) from exc
    return _camera_response(created)

# 2. إدارة المناطق المحظورة (Restricted Zones) لكل كاميرا
def _extract_zone_metadata(raw_polygon):
    if isinstance(raw_polygon, dict):
        points = raw_polygon.get("points", [])
        if isinstance(points, list) and points and isinstance(points[0], dict):
            points = [[point.get("x", 0), point.get("y", 0)] for point in points]
        return (
            points,
            raw_polygon.get("video_width"),
            raw_polygon.get("video_height"),
        )
    if isinstance(raw_polygon, list):
        return raw_polygon, None, None
    return raw_polygon, None, None


def _build_zone_response(zone: RestrictedZone):
    polygon_coords, video_width, video_height = _extract_zone_metadata(zone.polygon_coords)
    return {
        "zone_id": zone.zone_id,
        "zone_name": zone.zone_name,
        "zone_type": zone.zone_type,
        "polygon_coords": polygon_coords,
        "video_width": video_width,
        "video_height": video_height,
        "tripwire_allowed_group_size": zone.tripwire_allowed_group_size,
        "tripwire_initial_occupancy": zone.tripwire_initial_occupancy,
        "tripwire_current_occupancy": zone.tripwire_current_occupancy,
        "tripwire_entry_direction": zone.tripwire_entry_direction,
        "tripwire_requires_confirmation": bool(zone.tripwire_requires_confirmation),
    }


@router.post("/{camera_id}/zones", response_model=ZoneResponse)
def add_restricted_zone(camera_id: str, zone: ZoneCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_resource_user)):
    cam = _get_camera_for_user(db, camera_id, current_user)
    zone_name = zone.zone_name.strip()
    if not zone_name:
        raise HTTPException(status_code=422, detail="Zone name cannot be empty")
    is_tripwire = zone.zone_type.strip().lower() == "tripwire"
    if is_tripwire and (
        zone.tripwire_allowed_group_size is None
        or zone.tripwire_initial_occupancy is None
        or zone.tripwire_entry_direction not in {"left", "right"}
    ):
        raise HTTPException(
            status_code=422,
            detail="Tripwire configuration requires a positive group size, non-negative occupancy, and direction",
        )

    stored_polygon = {
        "points": zone.polygon_coords,
        "video_width": zone.video_width,
        "video_height": zone.video_height,
    }

    new_zone = RestrictedZone(
        camera_id=camera_id,
        zone_name=zone_name,
        zone_type=zone.zone_type,
        polygon_coords=stored_polygon,
        owner_id=cam.owner_id,
        customer_profile_id=cam.customer_profile_id,
        tripwire_allowed_group_size=zone.tripwire_allowed_group_size if is_tripwire else None,
        tripwire_initial_occupancy=zone.tripwire_initial_occupancy if is_tripwire else None,
        tripwire_current_occupancy=zone.tripwire_initial_occupancy if is_tripwire else None,
        tripwire_entry_direction=zone.tripwire_entry_direction if is_tripwire else None,
        tripwire_requires_confirmation=False,
    )
    db.add(new_zone)
    db.commit()
    db.refresh(new_zone)
    return _build_zone_response(new_zone)


@router.get("/{camera_id}/zones", response_model=list[ZoneResponse])
def list_restricted_zones(camera_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_resource_user)):
    _get_camera_for_user(db, camera_id, current_user)
    zones = (
        db.query(RestrictedZone)
        .filter(
            RestrictedZone.camera_id == camera_id,
            tenant_camera_child_filter(
                RestrictedZone,
                db,
                current_user.get("customer_profile_id"),
                owner_column=RestrictedZone.owner_id,
            ),
        )
        .all()
    )
    return [_build_zone_response(zone) for zone in zones]


@router.delete("/{camera_id}/zones/{zone_id}")
async def delete_restricted_zone(camera_id: str, zone_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_resource_user)):
    cam = _get_camera_for_user(db, camera_id, current_user)
    zone = db.query(RestrictedZone).filter(
        RestrictedZone.zone_id == zone_id,
        RestrictedZone.camera_id == camera_id,
        tenant_camera_child_filter(
            RestrictedZone,
            db,
            current_user.get("customer_profile_id"),
            owner_column=RestrictedZone.owner_id,
        ),
    ).first()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    is_tripwire = "tripwire" in (zone.zone_type or "").lower()
    db.delete(zone)
    db.commit()
    if is_tripwire:
        state = (
            ai_engine.clear_tripwire_alarm_state(camera_id, zone_id)
            if ai_engine is not None
            else None
        )
        await manager.broadcast(
            {
                "event": "tripwire_alarm_state",
                "data": {
                    "camera_id": str(camera_id),
                    "zone_id": str(zone_id),
                    "active": False,
                    "event_id": state.get("event_id") if state else None,
                },
            },
            audience_customer_profile_id=cam.customer_profile_id,
        )
    return {"message": "Zone deleted successfully"}


@router.post("/{camera_id}/zones/{zone_id}/tripwire/confirm", response_model=ZoneResponse)
def confirm_tripwire_occupancy(
    camera_id: str,
    zone_id: str,
    confirmation: TripwireOccupancyConfirmation,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_resource_user),
):
    _get_camera_for_user(db, camera_id, current_user)
    zone = db.query(RestrictedZone).filter(
        RestrictedZone.zone_id == zone_id,
        RestrictedZone.camera_id == camera_id,
        func.lower(RestrictedZone.zone_type) == "tripwire",
        tenant_camera_child_filter(
            RestrictedZone,
            db,
            current_user.get("customer_profile_id"),
            owner_column=RestrictedZone.owner_id,
        ),
    ).first()
    if not zone:
        raise HTTPException(status_code=404, detail="Tripwire not found")
    if confirmation.allowed_group_size is not None:
        zone.tripwire_allowed_group_size = confirmation.allowed_group_size
    if confirmation.zone_name is not None:
        zone_name = confirmation.zone_name.strip()
        if not zone_name:
            raise HTTPException(status_code=422, detail="Zone name cannot be empty")
        zone.zone_name = zone_name
    zone.tripwire_current_occupancy = confirmation.current_occupancy
    zone.tripwire_requires_confirmation = False
    db.commit()
    db.refresh(zone)
    return _build_zone_response(zone)

# 3. تشغيل الـ AI
@router.post("/{camera_id}/start")
async def start_analysis(camera_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db), current_user: dict = Depends(get_resource_user)):
    cam = _get_camera_for_user(db, camera_id, current_user)
    camera_type = (cam.camera_type or "").strip().upper()
    if ai_engine is None:
        raise HTTPException(status_code=503, detail="AI engine is currently unavailable")

    start_state = ai_engine.reserve_camera_startup(cam.camera_id)
    if start_state == "stopping":
        raise HTTPException(
            status_code=409,
            detail="Camera is stopping; retry the start request",
        )
    if start_state == "active":
        return {"status": "started", "camera_id": str(cam.camera_id)}
    if start_state == "starting":
        raise HTTPException(
            status_code=409,
            detail="Camera startup is already in progress",
        )

    startup_reservation_owned = True
    startup_activated = False
    worker_scheduled = False
    try:
        if camera_type in RTSP_CAMERA_TYPES:
            live_url = _validate_live_rtsp_url(cam.stream_url)
            await _verify_live_rtsp(live_url)
            try:
                go2rtc_service.register_stream(cam.camera_id, live_url)
            except Go2RTCError as exc:
                raise HTTPException(
                    status_code=503,
                    detail="go2rtc could not register this camera stream",
                ) from exc
            ai_source_url = resolve_camera_restream_url(
                str(cam.camera_id),
                live_url,
            )
            if ai_source_url is None:
                raise HTTPException(
                    status_code=503,
                    detail="go2rtc did not provide an AI restream URL",
                )
        else:
            ai_source_url = cam.stream_url

        if ai_engine.activate_camera_startup(cam.camera_id) != "reserved":
            startup_reservation_owned = False
            raise HTTPException(
                status_code=409,
                detail="Camera start was cancelled",
            )
        startup_reservation_owned = False
        startup_activated = True

        cam.status = "Processing"
        db.commit()
        if cam.camera_type in RTSP_CAMERA_TYPES:
            background_tasks.add_task(
                _run_live_camera,
                cam.camera_id,
                ai_source_url,
                True,
                camera_type,
            )
        else:
            background_tasks.add_task(
                ai_engine.process_camera,
                cam.camera_id,
                cam.stream_url,
                None,
                True,
                camera_type,
            )
        worker_scheduled = True
    finally:
        if startup_reservation_owned:
            ai_engine.release_camera_startup(cam.camera_id)
        elif startup_activated and not worker_scheduled:
            ai_engine.release_camera_start(cam.camera_id)
        if not worker_scheduled and cam.status == "Processing":
            cam.status = "Offline"
            db.commit()
            await manager.broadcast({
                "event": "camera_status",
                "data": {
                    "camera_id": str(cam.camera_id),
                    "status": "Offline",
                },
            }, audience_customer_profile_id=(
                cam.customer_profile_id
            ))
    return {"status": "started", "camera_id": str(cam.camera_id)}


@router.post("/{camera_id}/stop")
async def stop_analysis(camera_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_resource_user)):
    cam = _get_camera_for_user(db, camera_id, current_user)
    if ai_engine is None:
        raise HTTPException(status_code=503, detail="AI engine is currently unavailable")

    ai_engine.stop_camera(cam.camera_id)
    camera_key = str(cam.camera_id)
    with ai_engine._active_camera_lock:
        worker_active = camera_key in ai_engine._active_cameras
    if not worker_active:
        cam.status = resolve_camera_status(
            camera_key,
            "Offline",
            ai_engine.get_camera_runtime_statuses([camera_key]),
        )
        db.commit()
        await manager.broadcast({
            "event": "camera_status",
            "data": {
                "camera_id": camera_key,
                "status": cam.status,
            },
        }, audience_customer_profile_id=(
            cam.customer_profile_id
        ))
    return {"status": "stopped", "camera_id": str(cam.camera_id)}

# 4. جلب الكاميرات
@router.get("/", response_model=list[CameraResponse])
def get_cameras(db: Session = Depends(get_db), current_user: dict = Depends(get_resource_user)):
    repo = CameraRepository(db)
    cameras = repo.get_all_cameras(
        owner_id=current_user.get("user_id"),
        customer_profile_id=current_user.get("customer_profile_id"),
        platform_wide=current_user.get("role") == "Owner",
    )
    responses = [_camera_response(camera) for camera in cameras]
    apply_camera_runtime_statuses(responses, ai_engine)
    return responses

# 5. حذف كاميرا
@router.delete("/{camera_id}")
def delete_camera(camera_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_resource_user)):
    cam = _get_camera_for_user(db, camera_id, current_user)
    camera_type = (cam.camera_type or "").strip().upper()

    if camera_type in RTSP_CAMERA_TYPES:
        try:
            go2rtc_service.remove_stream(cam.camera_id)
        except Go2RTCError as exc:
            raise HTTPException(
                status_code=503,
                detail="Camera was not deleted because its go2rtc stream could not be removed",
            ) from exc

    if cam.camera_type == "UPLOAD" and cam.stream_url:
        try:
            abs_path = os.path.abspath(cam.stream_url)
            if os.path.commonpath([UPLOAD_DIR, abs_path]) == UPLOAD_DIR and os.path.exists(abs_path):
                os.remove(abs_path)
        except Exception as exc:
            print(f"⚠️ Failed to remove upload file for camera {camera_id}: {exc}")

    if ai_engine is not None:
        ai_engine.stop_camera(cam.camera_id)
        ai_engine.stop_camera_source(cam.camera_id, clear_frames=True)

    for related in db.query(AIEvent).filter(
        AIEvent.camera_id == cam.camera_id,
        tenant_camera_child_filter(
            AIEvent,
            db,
            current_user.get("customer_profile_id"),
            actor_column=AIEvent.detected_by,
        ),
    ).all():
        db.delete(related)
    for related in db.query(Detection).filter(
        Detection.camera_id == cam.camera_id,
        tenant_camera_child_filter(
            Detection,
            db,
            current_user.get("customer_profile_id"),
            owner_column=Detection.owner_id,
        ),
    ).all():
        db.delete(related)
    for related in db.query(Tracking).filter(
        Tracking.camera_id == cam.camera_id,
        tenant_camera_child_filter(
            Tracking,
            db,
            current_user.get("customer_profile_id"),
        ),
    ).all():
        db.delete(related)
    for related in db.query(RestrictedZone).filter(
        RestrictedZone.camera_id == cam.camera_id,
        tenant_camera_child_filter(
            RestrictedZone,
            db,
            current_user.get("customer_profile_id"),
            owner_column=RestrictedZone.owner_id,
        ),
    ).all():
        db.delete(related)

    db.delete(cam)
    db.commit()
    return {"status": "deleted", "camera_id": camera_id}

# 6. محرك البث (Streaming)
async def frame_generator(camera_id: str, sequential_playback: bool = False):
    last_sequence = 0
    last_diagnostic_sequence = 0
    initial_playback_frame = None
    if sequential_playback and ai_engine is not None:
        latest_playback_getter = getattr(
            ai_engine,
            "get_latest_file_playback_frame",
            None,
        )
        if callable(latest_playback_getter):
            initial_playback_frame = latest_playback_getter(camera_id)
            if initial_playback_frame is not None:
                last_sequence = initial_playback_frame[0] - 1

    while True:
        if sequential_playback and ai_engine is not None:
            playback_frame = initial_playback_frame
            initial_playback_frame = None
            if playback_frame is None:
                next_playback_getter = getattr(
                    ai_engine,
                    "get_next_file_playback_frame",
                    None,
                )
                if callable(next_playback_getter):
                    playback_frame = await asyncio.to_thread(
                        next_playback_getter,
                        camera_id,
                        last_sequence,
                        0.25,
                    )
            if playback_frame is None:
                await asyncio.sleep(0.02)
                continue

            sequence, payload, _timestamp = playback_frame
            if sequence == last_sequence:
                await asyncio.sleep(0.02)
                continue
            if sequence > last_sequence + 1:
                logger.warning(
                    "Uploaded video playback queue overrun camera=%s dropped_frames=%s",
                    camera_id,
                    sequence - last_sequence - 1,
                )
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n"
                + payload
                + b"\r\n"
            )
            last_sequence = sequence
            continue

        diagnostic_sequence = None
        capture_timestamp_ns = None
        snapshot = None
        if ai_engine is not None:
            live_getter = getattr(ai_engine, "get_live_frame_snapshot", None)
            if callable(live_getter):
                live_snapshot = live_getter(camera_id, last_sequence)
                if live_snapshot is not None:
                    snapshot = live_snapshot
            if snapshot is None and hasattr(ai_engine, "get_next_diagnostic_frame_snapshot"):
                diagnostic_snapshot = ai_engine.get_next_diagnostic_frame_snapshot(
                    camera_id,
                    last_diagnostic_sequence,
                )
                if diagnostic_snapshot is None:
                    latest_getter = getattr(ai_engine, "get_latest_frame_snapshot", None)
                    if callable(latest_getter):
                        snapshot = latest_getter(camera_id, last_sequence)
                else:
                    (
                        sequence,
                        frame,
                        diagnostic_sequence,
                        capture_timestamp_ns,
                    ) = diagnostic_snapshot
                    snapshot = (sequence, frame)
                    last_diagnostic_sequence = diagnostic_sequence
            elif snapshot is None:
                latest_getter = getattr(ai_engine, "get_latest_frame_snapshot", None)
                if callable(latest_getter):
                    snapshot = latest_getter(camera_id, last_sequence)
        if snapshot is None:
            await asyncio.sleep(0.02)
            continue

        sequence, frame = snapshot
        diagnostics = getattr(ai_engine, "frame_diagnostics", None)
        if diagnostics is not None and diagnostic_sequence is not None:
            diagnostics.record_frame(
                camera_id,
                diagnostic_sequence,
                "E",
                frame,
                capture_timestamp_ns,
            )
            diagnostics.record_frame(
                camera_id,
                diagnostic_sequence,
                "F",
                frame,
                capture_timestamp_ns,
            )
        if sequence == last_sequence:
            await asyncio.sleep(0.02)
            continue
        try:
            payload = await asyncio.to_thread(_encode_mjpeg_frame, frame)
            if payload is None:
                logger.warning(
                    "MJPEG frame rejected before send camera=%s sequence=%s",
                    camera_id,
                    sequence,
                )
            else:
                if diagnostics is not None and diagnostic_sequence is not None:
                    diagnostics.record_jpeg(
                        camera_id,
                        diagnostic_sequence,
                        payload,
                        capture_timestamp_ns,
                    )
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(
                        "camera frame stage=encoded camera=%s sequence=%s bytes=%s",
                        camera_id,
                        sequence,
                        len(payload),
                    )
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n"
                    + payload
                    + b"\r\n"
                )
        except Exception as exc:
            logger.warning(
                "MJPEG encoding failed camera=%s error=%s",
                camera_id,
                type(exc).__name__,
            )
        last_sequence = sequence

@router.get("/{camera_id}/stream")
async def get_stream(camera_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_resource_user)):
    cam = _get_camera_for_user(db, camera_id, current_user)
    if ai_engine is None:
        raise HTTPException(status_code=503, detail="AI engine is currently unavailable")
    return StreamingResponse(
        frame_generator(
            camera_id,
            sequential_playback=(cam.camera_type or "").strip().upper()
            == "UPLOAD",
        ),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )