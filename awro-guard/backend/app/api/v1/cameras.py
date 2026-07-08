import os
import shutil
import uuid
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import cv2
import asyncio

from ...database.session import get_db
from ...repositories.camera_repository import CameraRepository
from ...models.models import Camera, RestrictedZone
from ...schemas.schemas import CameraResponse, ZoneCreate
from ...ai.processor import ai_engine 

router = APIRouter(prefix="/cameras", tags=["Cameras"])

# مجلد حفظ الفيديوهات المرفوعة
UPLOAD_DIR = "uploads/videos"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 1. تسجيل كاميرا (بث مباشر أو رفع فيديو)
@router.post("/", response_model=CameraResponse)
async def add_camera(
    camera_name: str = Form(...),
    location: str = Form(...),
    camera_type: str = Form(...), # LIVE or UPLOAD
    stream_url: str = Form(None), # لروابط RTSP/IP
    video_file: UploadFile = File(None), # لرفع ملفات الفيديو
    db: Session = Depends(get_db)
):
    final_url = stream_url
    # دعم كاميرا الجهاز (USB/Webcam)
    if camera_type == "USB":
        final_url = "0"
    
    # معالجة رفع الفيديو إذا كان النوع UPLOAD
    if camera_type == "UPLOAD" and video_file:
        file_ext = video_file.filename.split(".")[-1]
        file_name = f"{uuid.uuid4()}.{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, file_name)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(video_file.file, buffer)
        final_url = file_path

    new_cam = Camera(
        camera_name=camera_name,
        location=location,
        stream_url=final_url,
        camera_type=camera_type,
        status="Online" if camera_type in ["UPLOAD", "USB"] else "Offline"
    )
    
    db.add(new_cam)
    db.commit()
    db.refresh(new_cam)
    return new_cam

# 2. إدارة المناطق المحظورة (Restricted Zones) لكل كاميرا
@router.post("/{camera_id}/zones")
def add_restricted_zone(camera_id: str, zone: ZoneCreate, db: Session = Depends(get_db)):
    new_zone = RestrictedZone(
        camera_id=camera_id,
        zone_name=zone.zone_name,
        zone_type=zone.zone_type,
        polygon_coords=zone.polygon_coords
    )
    db.add(new_zone)
    db.commit()
    return {"message": "Zone added successfully"}


@router.get("/{camera_id}/zones")
def list_restricted_zones(camera_id: str, db: Session = Depends(get_db)):
    zones = db.query(RestrictedZone).filter(RestrictedZone.camera_id == camera_id).all()
    return zones

# 3. تشغيل الـ AI
@router.post("/{camera_id}/start")
async def start_analysis(camera_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    cam = db.query(Camera).filter(Camera.camera_id == camera_id).first()
    if not cam: raise HTTPException(404)
    background_tasks.add_task(ai_engine.process_camera, cam.camera_id, cam.stream_url, db)
    return {"status": "started"}

# 4. جلب الكاميرات
@router.get("/", response_model=list[CameraResponse])
def get_cameras(db: Session = Depends(get_db)):
    return db.query(Camera).all()

# 5. محرك البث (Streaming)
async def frame_generator(camera_id: str):
    while True:
        frame = ai_engine.get_latest_frame(camera_id)
        if frame is not None:
            ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
            if ret:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        await asyncio.sleep(0.1)

@router.get("/{camera_id}/stream")
async def get_stream(camera_id: str):
    return StreamingResponse(frame_generator(camera_id), media_type='multipart/x-mixed-replace; boundary=frame')