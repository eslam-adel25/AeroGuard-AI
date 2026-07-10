from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from typing import Optional
from sqlalchemy.orm import Session
from ...database.session import get_db
from ...core.auth_middleware import get_current_user
from ...services.ai_service import AIService
from ...repositories.ai_repository import AIRepository
from fastapi.responses import FileResponse
import os

router = APIRouter()

@router.get("/ai/events")
def list_ai_events(camera_id: Optional[str] = None, limit: int = 100, offset: int = 0, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    repo = AIRepository(db)
    is_admin = current_user.get("role") == "Administrator"
    if camera_id and not is_admin:
        from ...models.models import Camera
        camera = db.query(Camera).filter(Camera.camera_id == camera_id).first()
        if not camera or camera.owner_id != current_user.get("user_id"):
            raise HTTPException(status_code=403, detail="Forbidden")
    items = repo.list_events(camera_id=camera_id, limit=limit, offset=offset)
    return {"items": [
        {
            "event_id": str(i.event_id),
            "camera_id": str(i.camera_id),
            "detection_type": i.detection_type,
            "severity": i.severity,
            "confidence": i.confidence,
            "screenshot_path": i.screenshot_path,
            "created_at": i.created_at.isoformat(),
            "metadata": i.event_metadata,
        } for i in items
    ]}

@router.get("/ai/events/{event_id}")
def get_ai_event(event_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    repo = AIRepository(db)
    ev = repo.get_event(event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")
    if current_user.get("role") != "Administrator" and ev.camera_id and ev.detected_by != current_user.get("user_id"):
        from ...models.models import Camera
        camera = db.query(Camera).filter(Camera.camera_id == ev.camera_id).first()
        if not camera or camera.owner_id != current_user.get("user_id"):
            raise HTTPException(status_code=403, detail="Forbidden")
    return {
        "event_id": str(ev.event_id),
        "camera_id": str(ev.camera_id),
        "detection_type": ev.detection_type,
        "severity": ev.severity,
        "confidence": ev.confidence,
        "screenshot_path": ev.screenshot_path,
        "created_at": ev.created_at.isoformat(),
        "metadata": ev.event_metadata,
    }

@router.post("/ai/events/manual")
async def create_ai_event_manual(camera_id: str, detection_type: str, severity: str, confidence: Optional[float] = None, file: Optional[UploadFile] = File(None), db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    svc = AIService(db)
    image_bytes = None
    if file:
        image_bytes = await file.read()
    ev = svc.register_event(camera_id=camera_id, detection_type=detection_type, severity=severity, confidence=confidence, user_id=current_user.get("user_id"), screenshot_bytes=image_bytes)
    return {"event_id": str(ev.event_id)}



@router.get("/ai/events/{event_id}/screenshot")
def get_ai_event_screenshot(event_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    repo = AIRepository(db)
    ev = repo.get_event(event_id)
    if not ev or not ev.screenshot_path:
        raise HTTPException(status_code=404, detail="Screenshot not found")
    if current_user.get("role") != "Administrator" and ev.camera_id and ev.detected_by != current_user.get("user_id"):
        from ...models.models import Camera
        camera = db.query(Camera).filter(Camera.camera_id == ev.camera_id).first()
        if not camera or camera.owner_id != current_user.get("user_id"):
            raise HTTPException(status_code=403, detail="Forbidden")
    path = ev.screenshot_path
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Screenshot file missing")
    filename = os.path.basename(path)
    return FileResponse(path, media_type="image/jpeg", filename=filename)
