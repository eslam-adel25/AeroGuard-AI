from __future__ import annotations

from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, date

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc

from ..models.models import AIEvent, Tracking, Camera
from ..core.tenant import tenant_camera_child_filter


class AIRepository:
    """Repository for AI events and tracking records.

    Provides CRUD operations, list/query with filtering, pagination,
    and helper queries used by reports and the dashboard.
    """

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def exclude_pending_events(query):
        pending = AIEvent.event_metadata["_pending_screenshot"].as_boolean()
        return query.filter(or_(pending.is_(None), pending.is_(False)))

    # -----------------
    # Tracking methods
    # -----------------
    def create_tracking(
        self,
        camera_id: str,
        track_type: str = "person",
        track_label: Optional[str] = None,
        latest_bbox: Optional[Dict[str, Any]] = None,
        confidence: Optional[float] = None,
    ) -> Tracking:
        camera = (
            self.db.query(Camera)
            .filter(Camera.camera_id == camera_id)
            .first()
        )
        if camera is None:
            raise ValueError("Camera not found")
        t = Tracking(
            camera_id=camera_id,
            customer_profile_id=camera.customer_profile_id,
            track_type=track_type,
            track_label=track_label,
            latest_bbox=latest_bbox,
            confidence=confidence,
        )
        self.db.add(t)
        self.db.commit()
        self.db.refresh(t)
        return t

    def get_tracking(self, track_id: str) -> Optional[Tracking]:
        return self.db.query(Tracking).filter(Tracking.track_id == track_id).first()

    def update_tracking(self, track_id: str, **kwargs: Any) -> Optional[Tracking]:
        t = self.get_tracking(track_id)
        if not t:
            return None
        for k, v in kwargs.items():
            if hasattr(t, k) and v is not None:
                setattr(t, k, v)
        self.db.add(t)
        self.db.commit()
        self.db.refresh(t)
        return t

    def list_trackings(
        self,
        camera_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        active_only: bool = False,
    ) -> List[Tracking]:
        q = self.db.query(Tracking)
        if camera_id:
            q = q.filter(Tracking.camera_id == camera_id)
        if active_only:
            q = q.filter(Tracking.last_seen_at.isnot(None))
        return q.order_by(desc(Tracking.last_seen_at)).limit(limit).offset(offset).all()

    # -----------------
    # AIEvent methods
    # -----------------
    def create_event(
        self,
        payload: Dict[str, Any],
    ) -> AIEvent:
        """Create an AIEvent. Expects payload keys matching model fields.

        Example payload keys: camera_id, detection_type, severity, confidence,
        track_id, detected_by, metadata, screenshot_path
        """
        # Accept payloads that may use the key 'metadata' (external callers).
        # Map it to the model attribute name `event_metadata` which is mapped
        # to the DB column "metadata" to preserve compatibility.
        if "metadata" in payload:
            payload["event_metadata"] = payload.pop("metadata")

        ev = AIEvent(**payload)
        self.db.add(ev)
        self.db.commit()
        self.db.refresh(ev)
        return ev

    def get_event(self, event_id: str) -> Optional[AIEvent]:
        return self.db.query(AIEvent).filter(AIEvent.event_id == event_id).first()

    def get_finalized_event(self, event_id: str) -> Optional[AIEvent]:
        query = self.db.query(AIEvent).filter(AIEvent.event_id == event_id)
        return self.exclude_pending_events(query).first()

    def update_event(self, event_id: str, **kwargs: Any) -> Optional[AIEvent]:
        ev = self.get_event(event_id)
        if not ev:
            return None
        # Allow callers to pass 'metadata' and map it to our model attribute.
        if "metadata" in kwargs:
            kwargs["event_metadata"] = kwargs.pop("metadata")
        for k, v in kwargs.items():
            if hasattr(ev, k) and v is not None:
                setattr(ev, k, v)
        self.db.add(ev)
        self.db.commit()
        self.db.refresh(ev)
        return ev

    def delete_event(self, event_id: str) -> bool:
        ev = self.get_event(event_id)
        if not ev:
            return False
        self.db.delete(ev)
        self.db.commit()
        return True

    def list_events(
        self,
        camera_id: Optional[str] = None,
        user_id: Optional[str] = None,
        owner_id: Optional[str] = None,
        exclude_pending_screenshots: bool = False,
        detection_type: Optional[str] = None,
        severity: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 100,
        offset: int = 0,
        customer_profile_id: Optional[str] = None,
    ) -> List[AIEvent]:
        q = self.db.query(AIEvent)
        filters = []
        if camera_id:
            filters.append(AIEvent.camera_id == camera_id)
        if user_id:
            filters.append(AIEvent.detected_by == user_id)
        if owner_id:
            q = q.join(Camera, Camera.camera_id == AIEvent.camera_id)
            filters.append(Camera.owner_id == owner_id)
        if customer_profile_id:
            filters.append(
                tenant_camera_child_filter(
                    AIEvent,
                    self.db,
                    customer_profile_id,
                    actor_column=AIEvent.detected_by,
                )
            )
        elif not owner_id:
            filters.append(False)
        if exclude_pending_screenshots:
            q = self.exclude_pending_events(q)
        if detection_type:
            filters.append(AIEvent.detection_type.ilike(f"%{detection_type}%"))
        if severity:
            filters.append(AIEvent.severity.ilike(f"%{severity}%"))
        if start_date:
            filters.append(func.date(AIEvent.created_at) >= start_date)
        if end_date:
            filters.append(func.date(AIEvent.created_at) <= end_date)
        if filters:
            q = q.filter(and_(*filters))
        q = q.order_by(AIEvent.created_at.desc()).limit(limit).offset(offset)
        return q.all()

    def count_unread_events(
        self,
        camera_id: Optional[str] = None,
        owner_id: Optional[str] = None,
        exclude_pending_screenshots: bool = False,
        customer_profile_id: Optional[str] = None,
    ) -> int:
        q = self.db.query(func.count(AIEvent.event_id)).filter(
            AIEvent.is_read.is_(False)
        )
        if camera_id:
            q = q.filter(AIEvent.camera_id == camera_id)
        if owner_id:
            q = q.join(Camera, Camera.camera_id == AIEvent.camera_id).filter(
                Camera.owner_id == owner_id
            )
        if customer_profile_id:
            q = q.filter(
                tenant_camera_child_filter(
                    AIEvent,
                    self.db,
                    customer_profile_id,
                    actor_column=AIEvent.detected_by,
                )
            )
        elif not owner_id:
            q = q.filter(False)
        if exclude_pending_screenshots:
            q = self.exclude_pending_events(q)
        return int(q.scalar() or 0)

    # For reports: returns (total, items)
    def query_events_for_report(
        self,
        camera_id: Optional[str] = None,
        owner_id: Optional[str] = None,
        detection_type: Optional[str] = None,
        severity: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 100,
        offset: int = 0,
        customer_profile_id: Optional[str] = None,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        q = self.db.query(
            AIEvent,
            Camera.camera_name,
            Camera.location,
        ).join(Camera, Camera.camera_id == AIEvent.camera_id)
        filters = []
        if camera_id:
            filters.append(AIEvent.camera_id == camera_id)
        if owner_id:
            filters.append(Camera.owner_id == owner_id)
        if customer_profile_id:
            filters.append(
                tenant_camera_child_filter(
                    AIEvent,
                    self.db,
                    customer_profile_id,
                    actor_column=AIEvent.detected_by,
                )
            )
        elif not owner_id:
            filters.append(False)
        if detection_type:
            filters.append(AIEvent.detection_type.ilike(f"%{detection_type}%"))
        if severity:
            filters.append(AIEvent.severity.ilike(f"%{severity}%"))
        if start_date:
            filters.append(func.date(AIEvent.created_at) >= start_date)
        if end_date:
            filters.append(func.date(AIEvent.created_at) <= end_date)
        if filters:
            q = q.filter(and_(*filters))
        q = self.exclude_pending_events(q)

        total = q.count()
        rows = q.order_by(AIEvent.created_at.desc()).limit(limit).offset(offset).all()

        items: List[Dict[str, Any]] = []
        for event, camera_name, location in rows:
            items.append(
                {
                    "event_id": str(event.event_id),
                    "camera_id": str(event.camera_id),
                    "camera_name": camera_name,
                    "location": location,
                    "detection_type": event.detection_type,
                    "severity": event.severity,
                    "confidence": float(event.confidence) if event.confidence is not None else None,
                    "screenshot_path": event.screenshot_path,
                    "metadata": event.event_metadata,
                    "created_at": event.created_at.isoformat() if event.created_at is not None else None,
                }
            )

        return total, items

    # Dashboard helper stats used by ReportService
    def get_event_counts_by_type(
        self,
        camera_id: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[Tuple[str, int]]:
        q = self.db.query(AIEvent.detection_type, func.count(AIEvent.event_id).label("count"))
        filters = []
        if camera_id:
            filters.append(AIEvent.camera_id == camera_id)
        if start_date:
            filters.append(func.date(AIEvent.created_at) >= start_date)
        if end_date:
            filters.append(func.date(AIEvent.created_at) <= end_date)
        pending = AIEvent.event_metadata["_pending_screenshot"].as_boolean()
        filters.append(or_(pending.is_(None), pending.is_(False)))
        if filters:
            q = q.filter(and_(*filters))
        q = q.group_by(AIEvent.detection_type)
        rows = q.all()
        return [(row.detection_type, int(row.count or 0)) for row in rows]

    def recent_events(self, limit: int = 20) -> List[Dict[str, Any]]:
        rows = (
            self.exclude_pending_events(self.db.query(AIEvent))
            .order_by(AIEvent.created_at.desc())
            .limit(limit)
            .all()
        )
        result: List[Dict[str, Any]] = []
        for r in rows:
            result.append(
                {
                    "event_id": str(r.event_id),
                    "camera_id": str(r.camera_id),
                    "detection_type": r.detection_type,
                    "severity": r.severity,
                    "confidence": float(r.confidence) if r.confidence is not None else None,
                    "screenshot_path": r.screenshot_path,
                    "created_at": r.created_at.isoformat() if r.created_at is not None else None,
                }
            )
        return result
