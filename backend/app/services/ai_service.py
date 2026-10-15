import logging
import os
import re
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from ..repositories.ai_repository import AIRepository
from ..websocket.manager import manager
from ..models.models import Camera

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads", "ai_events")
os.makedirs(UPLOAD_DIR, exist_ok=True)
logger = logging.getLogger(__name__)


def _safe_filename_component(value: Optional[str]) -> str:
    if not value:
        return "unknown"
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", value.strip())
    normalized = normalized.strip("_")
    return normalized or "unknown"


def build_screenshot_filename(
    camera_name: Optional[str],
    detection_type: str,
    when: datetime,
) -> str:
    camera_part = _safe_filename_component(camera_name or "camera")
    type_part = _safe_filename_component(detection_type or "alert")
    timestamp = when.strftime("%Y-%m-%d_%H-%M-%S")
    return f"{camera_part}_{type_part}_{timestamp}.jpg"


class AIService:
    def __init__(self, db_session):
        self.repo = AIRepository(db_session)

    def _save_screenshot(
        self,
        image_bytes: bytes,
        camera_name: Optional[str] = None,
        detection_type: str = "event",
        when: Optional[datetime] = None,
    ) -> str:
        when = when or datetime.utcnow()
        filename = build_screenshot_filename(camera_name, detection_type, when)
        path = os.path.join(UPLOAD_DIR, filename)
        if os.path.exists(path):
            unique_suffix = uuid.uuid4().hex[:8]
            filename = f"{os.path.splitext(filename)[0]}_{unique_suffix}.jpg"
            path = os.path.join(UPLOAD_DIR, filename)
        with open(path, "wb") as f:
            f.write(image_bytes)
        return path

    def register_event(
        self,
        camera_id: str,
        detection_type: str,
        severity: str,
        confidence: Optional[float] = None,
        track_id: Optional[str] = None,
        user_id: Optional[str] = None,
        owner_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        screenshot_bytes: Optional[bytes] = None,
        broadcast: bool = True,
    ):
        payload = {
            "camera_id": camera_id,
            "detected_by": user_id or owner_id,
            "detection_type": detection_type,
            "severity": severity,
            "confidence": confidence,
            "metadata": metadata or {},
        }
        camera = None
        if hasattr(self.repo, "db") and hasattr(self.repo.db, "query"):
            try:
                camera = self.repo.db.query(Camera).filter(Camera.camera_id == camera_id).first()
            except Exception:
                camera = None
        if owner_id is not None and hasattr(self.repo, "db") and hasattr(self.repo.db, "query"):
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
                camera_name = getattr(camera, "camera_name", None) if camera else None
                path = self._save_screenshot(
                    screenshot_bytes,
                    camera_name=camera_name,
                    detection_type=detection_type,
                    when=datetime.utcnow(),
                )
                payload["screenshot_path"] = path
            except Exception:
                logger.exception("Failed to persist AI event screenshot")
                payload["screenshot_path"] = None
        ev = self.repo.create_event(payload)
        if broadcast:
            # send websocket notification (non-blocking callers should await if needed)
            try:
                import asyncio
                asyncio.create_task(manager.broadcast(
                    {
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
                    },
                    audience_user_id=(
                        str(getattr(camera, "owner_id", "")) if camera else None
                    ),
                ))
            except Exception:
                # if websocket manager unavailable, continue silently
                pass
        return ev

    async def attach_screenshot(self, event_id: str, image_bytes: bytes):
        ev = self.repo.get_event(event_id)
        if not ev or ev.screenshot_path:
            return ev

        camera = None
        if hasattr(self.repo, "db") and hasattr(self.repo.db, "query"):
            try:
                camera = self.repo.db.query(Camera).filter(Camera.camera_id == ev.camera_id).first()
            except Exception:
                camera = None

        try:
            path = self._save_screenshot(
                image_bytes,
                camera_name=getattr(camera, "camera_name", None) if camera else None,
                detection_type=ev.detection_type,
                when=datetime.utcnow(),
            )
        except Exception:
            return ev

        metadata = dict(ev.event_metadata or {})
        metadata.pop("_pending_screenshot", None)
        ev = self.repo.update_event(
            str(ev.event_id),
            screenshot_path=path,
            event_metadata=metadata,
        )
        if ev is None:
            return None

        try:
            await manager.broadcast(
                {
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
                },
                audience_user_id=(
                    str(
                        getattr(camera, "owner_id", None)
                        or getattr(ev, "detected_by", "")
                    )
                ),
            )
        except Exception:
            pass
        return ev
        