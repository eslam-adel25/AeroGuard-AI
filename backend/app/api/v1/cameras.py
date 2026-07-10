import os
import shutil
import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import cv2
import asyncio

from ...database.session import get_db
from ...models.models import Camera, RestrictedZone
from ...schemas.schemas import CameraResponse, ZoneCreate
from ...core.auth_middleware import get_current_user
from ...repositories.camera_repository import CameraRepository
from ...ai.processor import ai_engine 

router = APIRouter(prefix="/cameras", tags=["Cameras"])

# المجلد الجذري لوحدة backend
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
UPLOAD_DIR = Path(BASE_DIR) / "uploads" / "videos"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_VIDEO_EXTENSIONS = {"mp4", "mov", "avi", "mkv", "webm"}
MAX_VIDEO_SIZE = 200 * 1024 * 1024

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
@router.post("/{camera_id}/zones")
def add_restricted_zone(camera_id: str, zone: ZoneCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    # verify camera ownership
    cam = db.query(Camera).filter(Camera.camera_id == camera_id).first()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    if cam.owner_id != current_user.get("user_id") and current_user.get("role") != "Administrator":
        raise HTTPException(status_code=403, detail="Forbidden")

    new_zone = RestrictedZone(
        camera_id=camera_id,
        zone_name=zone.zone_name,
        zone_type=zone.zone_type,
        polygon_coords=zone.polygon_coords,
        owner_id=current_user.get("user_id")
    )
    db.add(new_zone)
    db.commit()
    return {"message": "Zone added successfully"}


@router.get("/{camera_id}/zones")
def list_restricted_zones(camera_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    cam = db.query(Camera).filter(Camera.camera_id == camera_id).first()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    if cam.owner_id != current_user.get("user_id") and current_user.get("role") != "Administrator":
        raise HTTPException(status_code=403, detail="Forbidden")
    zones = db.query(RestrictedZone).filter(RestrictedZone.camera_id == camera_id).all()
    return zones

# 3. تشغيل الـ AI
@router.post("/{camera_id}/start")
async def start_analysis(camera_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    cam = db.query(Camera).filter(Camera.camera_id == camera_id).first()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    if cam.owner_id != current_user.get("user_id") and current_user.get("role") != "Administrator":
        raise HTTPException(status_code=403, detail="Forbidden")
    background_tasks.add_task(ai_engine.process_camera, cam.camera_id, cam.stream_url)
    return {"status": "started"}

# 4. جلب الكاميرات
@router.get("/", response_model=list[CameraResponse])
def get_cameras(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    repo = CameraRepository(db)
    is_admin = current_user.get("role") == "Administrator"
    return repo.get_all_cameras(owner_id=current_user.get("user_id"), is_admin=is_admin)

# 5. حذف كاميرا
@router.delete("/{camera_id}")
def delete_camera(camera_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    cam = db.query(Camera).filter(Camera.camera_id == camera_id).first()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    if cam.owner_id != current_user.get("user_id") and current_user.get("role") != "Administrator":
        raise HTTPException(status_code=403, detail="Forbidden")

    if cam.camera_type == "UPLOAD" and cam.stream_url:
        try:
            abs_path = os.path.abspath(cam.stream_url)
            if os.path.commonpath([UPLOAD_DIR, abs_path]) == UPLOAD_DIR and os.path.exists(abs_path):
                os.remove(abs_path)
        except Exception as exc:
            print(f"⚠️ Failed to remove upload file for camera {camera_id}: {exc}")

    ai_engine.stop_camera(cam.camera_id)
    ai_engine.last_frames.pop(str(cam.camera_id), None)
    db.delete(cam)
    db.commit()
    return {"status": "deleted", "camera_id": camera_id}

# 6. محرك البث (Streaming)
async def frame_generator(camera_id: str):
    iteration = 0
    while True:
        iteration += 1
        frame = ai_engine.get_latest_frame(camera_id)
        if frame is not None:
            ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
            print(f"📌 [stream {camera_id}] generator iter={iteration} frame_present=True encoded={ret}")
            if ret:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        else:
            print(f"📌 [stream {camera_id}] generator iter={iteration} no frame available")
        await asyncio.sleep(0.1)

@router.get("/{camera_id}/stream")
async def get_stream(camera_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    cam = db.query(Camera).filter(Camera.camera_id == camera_id).first()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    if cam.owner_id != current_user.get("user_id") and current_user.get("role") != "Administrator":
        raise HTTPException(status_code=403, detail="Forbidden")
    return StreamingResponse(frame_generator(camera_id), media_type='multipart/x-mixed-replace; boundary=frame')