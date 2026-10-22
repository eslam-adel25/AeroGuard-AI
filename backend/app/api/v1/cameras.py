import os
import shutil
import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session
import cv2
import asyncio
from urllib.parse import urlparse

from ...database.session import get_db
from ...models.models import Camera, RestrictedZone, AIEvent, Detection, Tracking
from ...schemas.schemas import (
    CameraResponse,
    TripwireOccupancyConfirmation,
    ZoneCreate,
    ZoneResponse,
)
from ...core.auth_middleware import get_current_user
from ...repositories.camera_repository import CameraRepository
from ...services.camera_status import apply_camera_runtime_statuses
from ...ai.processor import ai_engine 
from ...websocket.manager import manager

router = APIRouter(prefix="/cameras", tags=["Cameras"])


def _get_camera_for_user(db: Session, camera_id: str, current_user: dict):
    cam = db.query(Camera).filter(Camera.camera_id == camera_id).first()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    if current_user.get("role") != "Administrator" and cam.owner_id != current_user.get("user_id"):
        raise HTTPException(status_code=403, detail="Forbidden")
    return cam

# المجلد الجذري لوحدة backend
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
UPLOAD_DIR = Path(BASE_DIR) / "uploads" / "videos"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_VIDEO_EXTENSIONS = {"mp4", "mov", "avi", "mkv", "webm"}
MAX_VIDEO_SIZE = 200 * 1024 * 1024
LIVE_PROBE_TIMEOUT_SECONDS = 10


def _validate_live_rtsp_url(stream_url: str) -> str:
    value = (stream_url or "").strip()
    parsed = urlparse(value)
    if parsed.scheme not in {"rtsp", "rtsps"} or not parsed.netloc:
        raise HTTPException(status_code=400, detail="A valid RTSP URL is required")
    return value


def _probe_live_rtsp(stream_url: str) -> bool:
    capture = cv2.VideoCapture()
    try:
        capture.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, LIVE_PROBE_TIMEOUT_SECONDS * 1000)
        capture.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, LIVE_PROBE_TIMEOUT_SECONDS * 1000)
        if not capture.open(stream_url):
            return False
        if not capture.isOpened():
            return False
        ret, frame = capture.read()
        return bool(ret and frame is not None and frame.size > 0)
    finally:
        capture.release()


async def _verify_live_rtsp(stream_url: str) -> None:
    try:
        available = await asyncio.wait_for(
            asyncio.to_thread(_probe_live_rtsp, stream_url),
            timeout=LIVE_PROBE_TIMEOUT_SECONDS + 1,
        )
    except Exception:
        available = False
    if not available:
        raise HTTPException(
            status_code=400,
            detail="The RTSP camera could not be opened or did not provide a frame",
        )


async def _run_live_camera(
    camera_id: str,
    stream_url: str,
    reserved: bool = False,
) -> None:
    await ai_engine.process_camera(
        camera_id,
        stream_url,
        reserved=reserved,
    )

# 1. تسجيل كاميرا (بث مباشر أو رفع فيديو)
@router.post("/", response_model=CameraResponse)
async def add_camera(
    camera_name: str = Form(...),
    location: str = Form(...),
    camera_type: str = Form(...), # LIVE or UPLOAD
    stream_url: str = Form(None), # لروابط RTSP/IP
    video_file: UploadFile = File(None), # لرفع ملفات الفيديو
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    final_url = stream_url
    if camera_type == "LIVE":
        final_url = _validate_live_rtsp_url(stream_url)
        await _verify_live_rtsp(final_url)
    # دعم كاميرا الجهاز (USB/Webcam)
    if camera_type == "USB":
        final_url = "0"
    
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
        file_path = UPLOAD_DIR / safe_name
        with file_path.open("wb") as buffer:
            buffer.write(contents)
        final_url = str(file_path)

    new_cam = Camera(
        camera_name=camera_name,
        location=location,
        stream_url=final_url,
        camera_type=camera_type,
        status="Online" if camera_type in ["UPLOAD", "USB"] else "Offline"
    )
    repo = CameraRepository(db)
    is_admin = current_user.get("role") == "Administrator"
    created = repo.add_camera(new_cam, owner_id=current_user.get("user_id"))
    return created

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
def add_restricted_zone(camera_id: str, zone: ZoneCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
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
        owner_id=current_user.get("user_id"),
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
def list_restricted_zones(camera_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    cam = _get_camera_for_user(db, camera_id, current_user)
    zones = db.query(RestrictedZone).filter(RestrictedZone.camera_id == camera_id).all()
    return [_build_zone_response(zone) for zone in zones]


@router.delete("/{camera_id}/zones/{zone_id}")
def delete_restricted_zone(camera_id: str, zone_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    cam = _get_camera_for_user(db, camera_id, current_user)
    zone = db.query(RestrictedZone).filter(
        RestrictedZone.zone_id == zone_id,
        RestrictedZone.camera_id == camera_id,
    ).first()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    db.delete(zone)
    db.commit()
    return {"message": "Zone deleted successfully"}


@router.post("/{camera_id}/zones/{zone_id}/tripwire/confirm", response_model=ZoneResponse)
def confirm_tripwire_occupancy(
    camera_id: str,
    zone_id: str,
    confirmation: TripwireOccupancyConfirmation,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    _get_camera_for_user(db, camera_id, current_user)
    zone = db.query(RestrictedZone).filter(
        RestrictedZone.zone_id == zone_id,
        RestrictedZone.camera_id == camera_id,
        func.lower(RestrictedZone.zone_type) == "tripwire",
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
async def start_analysis(camera_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    cam = _get_camera_for_user(db, camera_id, current_user)
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
        if cam.camera_type == "LIVE":
            live_url = _validate_live_rtsp_url(cam.stream_url)
            await _verify_live_rtsp(live_url)

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
        if cam.camera_type == "LIVE":
            background_tasks.add_task(
                _run_live_camera,
                cam.camera_id,
                cam.stream_url,
                True,
            )
        else:
            background_tasks.add_task(
                ai_engine.process_camera,
                cam.camera_id,
                cam.stream_url,
                None,
                True,
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
            })
    return {"status": "started", "camera_id": str(cam.camera_id)}


@router.post("/{camera_id}/stop")
async def stop_analysis(camera_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    cam = _get_camera_for_user(db, camera_id, current_user)
    if ai_engine is None:
        raise HTTPException(status_code=503, detail="AI engine is currently unavailable")

    ai_engine.stop_camera(cam.camera_id)
    camera_key = str(cam.camera_id)
    with ai_engine._active_camera_lock:
        worker_active = camera_key in ai_engine._active_cameras
    if not worker_active:
        cam.status = "Offline"
        db.commit()
        await manager.broadcast({
            "event": "camera_status",
            "data": {
                "camera_id": camera_key,
                "status": "Offline",
            },
        })
    return {"status": "stopped", "camera_id": str(cam.camera_id)}

# 4. جلب الكاميرات
@router.get("/", response_model=list[CameraResponse])
def get_cameras(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    repo = CameraRepository(db)
    is_admin = current_user.get("role") == "Administrator"
    cameras = repo.get_all_cameras(
        owner_id=current_user.get("user_id"), is_admin=is_admin
    )
    responses = [CameraResponse.model_validate(camera) for camera in cameras]
    apply_camera_runtime_statuses(responses, ai_engine)
    return responses

# 5. حذف كاميرا
@router.delete("/{camera_id}")
def delete_camera(camera_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    cam = _get_camera_for_user(db, camera_id, current_user)

    if cam.camera_type == "UPLOAD" and cam.stream_url:
        try:
            abs_path = os.path.abspath(cam.stream_url)
            if os.path.commonpath([UPLOAD_DIR, abs_path]) == UPLOAD_DIR and os.path.exists(abs_path):
                os.remove(abs_path)
        except Exception as exc:
            print(f"⚠️ Failed to remove upload file for camera {camera_id}: {exc}")

    if ai_engine is not None:
        ai_engine.stop_camera(cam.camera_id)
        ai_engine.last_frames.pop(str(cam.camera_id), None)

    for related in db.query(AIEvent).filter(AIEvent.camera_id == cam.camera_id).all():
        db.delete(related)
    for related in db.query(Detection).filter(Detection.camera_id == cam.camera_id).all():
        db.delete(related)
    for related in db.query(Tracking).filter(Tracking.camera_id == cam.camera_id).all():
        db.delete(related)
    for related in db.query(RestrictedZone).filter(RestrictedZone.camera_id == cam.camera_id).all():
        db.delete(related)

    db.delete(cam)
    db.commit()
    return {"status": "deleted", "camera_id": camera_id}

# 6. محرك البث (Streaming)
async def frame_generator(camera_id: str):
    iteration = 0
    while True:
        iteration += 1
        frame = None
        if ai_engine is not None:
            frame = ai_engine.get_latest_frame(camera_id)

        if frame is not None:
            try:
                ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
                if ret:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            except Exception as exc:
                print(f"⚠️ [stream {camera_id}] frame encode failed: {exc}")
        else:
            await asyncio.sleep(0.2)
            continue
        await asyncio.sleep(0.05)

@router.get("/{camera_id}/stream")
async def get_stream(camera_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    cam = _get_camera_for_user(db, camera_id, current_user)
    if ai_engine is None:
        raise HTTPException(status_code=503, detail="AI engine is currently unavailable")
    return StreamingResponse(frame_generator(camera_id), media_type='multipart/x-mixed-replace; boundary=frame')