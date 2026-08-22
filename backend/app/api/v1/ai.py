from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from ...database.session import get_db
from ...core.auth_middleware import get_current_user
from ...services.ai_service import AIService, build_screenshot_filename
from ...repositories.ai_repository import AIRepository
from ...models.models import AIEvent, Camera
from fastapi.responses import FileResponse
import os
from datetime import datetime

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
    owner_id = None if is_admin else current_user.get("user_id")
    items = repo.list_events(camera_id=camera_id, owner_id=owner_id, limit=limit, offset=offset)
    return {"items": [
        {
            "event_id": str(i.event_id),
            "camera_id": str(i.camera_id),
            "detection_type": i.detection_type,
            "severity": i.severity,
            "confidence": i.confidence,
            "screenshot_path": i.screenshot_path,
            "created_at": i.created_at.isoformat(),
            "status": "Read" if i.is_read else "Unread",
            "metadata": i.event_metadata,
        } for i in items
    ]}

@router.patch("/ai/events/{event_id}/read")
def mark_ai_event_read(event_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    repo = AIRepository(db)
    event = repo.get_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if current_user.get("role") != "Administrator":
        camera = db.query(Camera).filter(Camera.camera_id == event.camera_id).first()
        if not camera or str(camera.owner_id) != str(current_user.get("user_id")):
            raise HTTPException(status_code=403, detail="Forbidden")
    event.is_read = True
    db.commit()
    return {"event_id": str(event.event_id), "status": "Read"}

@router.post("/ai/events/read-all")
def mark_all_ai_events_read(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    owner_id = current_user.get("user_id")
    query = db.query(AIEvent)
    if current_user.get("role") != "Administrator":
        camera_ids = select(Camera.camera_id).where(Camera.owner_id == owner_id)
        query = query.filter(AIEvent.camera_id.in_(camera_ids))
    updated = query.filter(AIEvent.is_read.is_(False)).update(
        {AIEvent.is_read: True}, synchronize_session=False
    )
    db.commit()
    return {"updated": updated}

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
        "status": "Read" if ev.is_read else "Unread",
        "metadata": ev.event_metadata,
    }

@router.post("/ai/events/manual")
async def create_ai_event_manual(camera_id: str, detection_type: str, severity: str, confidence: Optional[float] = None, file: Optional[UploadFile] = File(None), db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    from ...models.models import Camera
    cam = db.query(Camera).filter(Camera.camera_id == camera_id).first()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    if current_user.get("role") != "Administrator" and cam.owner_id != current_user.get("user_id"):
        raise HTTPException(status_code=403, detail="Forbidden")

    svc = AIService(db)
    image_bytes = None
    if file:
        image_bytes = await file.read()
    ev = svc.register_event(
        camera_id=camera_id,
        detection_type=detection_type,
        severity=severity,
        confidence=confidence,
        user_id=current_user.get("user_id"),
        owner_id=current_user.get("user_id"),
        screenshot_bytes=image_bytes,
    )
    return {"event_id": str(ev.event_id)}



@router.get("/ai/events/{event_id}/screenshot")
def get_ai_event_screenshot(event_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    repo = AIRepository(db)
    ev = repo.get_event(event_id)
    if not ev or not ev.screenshot_path:
        raise HTTPException(status_code=404, detail="Screenshot not found")
    if current_user.get("role") != "Administrator" and ev.camera_id:
        from ...models.models import Camera
        camera = db.query(Camera).filter(Camera.camera_id == ev.camera_id).first()
        if not camera or camera.owner_id != current_user.get("user_id"):
            raise HTTPException(status_code=403, detail="Forbidden")
    path = ev.screenshot_path
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Screenshot file missing")
    camera = db.query(Camera).filter(Camera.camera_id == ev.camera_id).first()
    filename = build_screenshot_filename(
        getattr(camera, "camera_name", None) if camera else None,
        ev.detection_type,
        ev.created_at or datetime.utcnow(),
    )
    return FileResponse(path, media_type="image/jpeg", filename=filename)
