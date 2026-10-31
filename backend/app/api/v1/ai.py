from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import String, cast
from ...database.session import get_db
from ...core.auth_middleware import (
    get_resource_user,
    require_tenant_isolation,
)
from ...core.customer_features import (
    require_any_customer_feature,
    require_customer_feature,
)
from ...services.ai_service import AIService, build_screenshot_filename
from ...repositories.ai_repository import AIRepository
from ...models.models import AIEvent, Camera
from ...core.tenant import tenant_camera_child_filter, tenant_owner_filter
from fastapi.responses import FileResponse
import os
from datetime import datetime

router = APIRouter(dependencies=[Depends(require_tenant_isolation)])

@router.get("/ai/events")
def list_ai_events(camera_id: Optional[str] = None, event_id_prefix: Optional[str] = None, limit: int = 100, offset: int = 0, db: Session = Depends(get_db), current_user: dict = Depends(get_resource_user), _feature_access: dict = Depends(require_any_customer_feature("alerts", "analytics"))):
    repo = AIRepository(db)
    tenant_id = current_user.get("customer_profile_id")
    if camera_id:
        camera = db.query(Camera).filter(
            Camera.camera_id == camera_id,
            tenant_owner_filter(
                Camera,
                db,
                tenant_id,
                Camera.owner_id,
            ),
        ).first()
        if not camera:
            raise HTTPException(status_code=404, detail="Camera not found")
    if event_id_prefix is not None:
        prefix = event_id_prefix.strip()
        if len(prefix) < 4 or any(char not in "0123456789abcdefABCDEF-" for char in prefix):
            raise HTTPException(status_code=422, detail="Invalid Event ID prefix")

        event_query = db.query(AIEvent)
        event_query = event_query.filter(
            tenant_camera_child_filter(
                AIEvent,
                db,
                tenant_id,
                actor_column=AIEvent.detected_by,
            )
        )
        if camera_id:
            event_query = event_query.filter(AIEvent.camera_id == camera_id)
        event_query = repo.exclude_pending_events(event_query)
        items = (
            event_query.filter(cast(AIEvent.event_id, String).ilike(f"{prefix}%"))
            .order_by(AIEvent.created_at.desc())
            .limit(min(limit, 8))
            .offset(offset)
            .all()
        )
    else:
        items = repo.list_events(
            camera_id=camera_id,
            customer_profile_id=tenant_id,
            exclude_pending_screenshots=True,
            limit=limit,
            offset=offset,
        )
    return {
        "items": [
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
            }
            for i in items
        ],
        "unread_count": repo.count_unread_events(
            camera_id=camera_id,
            customer_profile_id=tenant_id,
            exclude_pending_screenshots=True,
        ),
    }

@router.patch("/ai/events/{event_id}/read")
def mark_ai_event_read(event_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_resource_user), _alerts_feature: dict = Depends(require_customer_feature("alerts"))):
    repo = AIRepository(db)
    tenant_id = current_user.get("customer_profile_id")
    event = repo.get_finalized_event(event_id)
    if event and not db.query(AIEvent).filter(
        AIEvent.event_id == event.event_id,
        tenant_camera_child_filter(
            AIEvent,
            db,
            tenant_id,
            actor_column=AIEvent.detected_by,
        ),
    ).first():
        event = None
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    event.is_read = True
    db.commit()
    return {"event_id": str(event.event_id), "status": "Read"}

@router.post("/ai/events/read-all")
def mark_all_ai_events_read(db: Session = Depends(get_db), current_user: dict = Depends(get_resource_user), _alerts_feature: dict = Depends(require_customer_feature("alerts"))):
    repo = AIRepository(db)
    tenant_id = current_user.get("customer_profile_id")
    query = db.query(AIEvent)
    query = query.filter(
        tenant_camera_child_filter(
            AIEvent,
            db,
            tenant_id,
            actor_column=AIEvent.detected_by,
        )
    )
    query = repo.exclude_pending_events(query)
    updated = query.filter(AIEvent.is_read.is_(False)).update(
        {AIEvent.is_read: True}, synchronize_session=False
    )
    db.commit()
    return {"updated": updated}

@router.get("/ai/events/{event_id}")
def get_ai_event(event_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_resource_user), _feature_access: dict = Depends(require_any_customer_feature("alerts", "analytics"))):
    repo = AIRepository(db)
    ev = repo.get_finalized_event(event_id)
    if ev and not db.query(AIEvent).filter(
        AIEvent.event_id == ev.event_id,
        tenant_camera_child_filter(
            AIEvent,
            db,
            current_user.get("customer_profile_id"),
            actor_column=AIEvent.detected_by,
        ),
    ).first():
        ev = None
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")
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
async def create_ai_event_manual(camera_id: str, detection_type: str, severity: str, confidence: Optional[float] = None, file: Optional[UploadFile] = File(None), db: Session = Depends(get_db), current_user: dict = Depends(get_resource_user), _alerts_feature: dict = Depends(require_customer_feature("alerts")), _camera_feature: dict = Depends(require_customer_feature("cameras"))):
    from ...models.models import Camera
    tenant_id = current_user.get("customer_profile_id")
    cam = db.query(Camera).filter(
        Camera.camera_id == camera_id,
        tenant_owner_filter(Camera, db, tenant_id, Camera.owner_id),
    ).first()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")

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
        customer_profile_id=cam.customer_profile_id,
        screenshot_bytes=image_bytes,
    )
    return {"event_id": str(ev.event_id)}



@router.get("/ai/events/{event_id}/screenshot")
def get_ai_event_screenshot(event_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_resource_user), _feature_access: dict = Depends(require_any_customer_feature("alerts", "analytics"))):
    repo = AIRepository(db)
    ev = repo.get_finalized_event(event_id)
    if ev and not db.query(AIEvent).filter(
        AIEvent.event_id == ev.event_id,
        tenant_camera_child_filter(
            AIEvent,
            db,
            current_user.get("customer_profile_id"),
            actor_column=AIEvent.detected_by,
        ),
    ).first():
        ev = None
    if not ev or not ev.screenshot_path:
        raise HTTPException(status_code=404, detail="Screenshot not found")
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
