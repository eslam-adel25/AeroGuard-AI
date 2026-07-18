import os
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from ..repositories.ai_repository import AIRepository
from ..websocket.manager import manager
from ..models.models import Camera

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads", "ai_events")
os.makedirs(UPLOAD_DIR, exist_ok=True)

class AIService:
    def __init__(self, db_session):
        self.repo = AIRepository(db_session)

    def _save_screenshot(self, image_bytes: bytes, prefix: str = "event") -> str:
        filename = f"{prefix}_{uuid.uuid4().hex}_{int(datetime.utcnow().timestamp())}.jpg"
        path = os.path.join(UPLOAD_DIR, filename)
        with open(path, "wb") as f:
            f.write(image_bytes)
        # return relative path from project root
        return path

    def register_event(self, camera_id: str, detection_type: str, severity: str, confidence: Optional[float] = None, track_id: Optional[str] = None, user_id: Optional[str] = None, owner_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None, screenshot_bytes: Optional[bytes] = None):
        payload = {
            "camera_id": camera_id,
            "detected_by": user_id or owner_id,
            "detection_type": detection_type,
            "severity": severity,
            "confidence": confidence,
            "metadata": metadata or {},
        }
        if owner_id is not None and hasattr(self.repo.db, "query"):
            try:
                camera = self.repo.db.query(Camera).filter(Camera.camera_id == camera_id).first()
            except Exception:
                camera = None
            if not camera:
                raise ValueError("Camera not found")
            if str(getattr(camera, "owner_id", None)) != str(owner_id):
                raise PermissionError("Camera ownership mismatch")
        if track_id is not None:
            try:
                payload["track_id"] = str(track_id)
                # Only keep UUID-compatible values; otherwise leave it unset.
                import uuid
                uuid.UUID(str(track_id))
            except Exception:
                payload["track_id"] = None
        if screenshot_bytes:
            try:
                path = self._save_screenshot(screenshot_bytes, prefix=detection_type.lower())
                payload["screenshot_path"] = path
            except Exception:
                payload["screenshot_path"] = None
        ev = self.repo.create_event(payload)
        # send websocket notification (non-blocking callers should await if needed)
        try:
            import asyncio
            asyncio.create_task(manager.broadcast({
                "event": "ai_event",
                "data": {
                    "event_id": str(ev.event_id),
                    "camera_id": str(ev.camera_id),
                    "detection_type": ev.detection_type,
                    "severity": ev.severity,
                    "confidence": ev.confidence,
                    "created_at": ev.created_at.isoformat(),
                    "screenshot": ev.screenshot_path,
                }
            }))
        except Exception:
            # if websocket manager unavailable, continue silently
            pass
        return ev
        