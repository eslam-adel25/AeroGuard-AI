import os
import sys
import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database.session import Base
from app.models.models import AIEvent, Camera, User
from app.repositories.camera_repository import CameraRepository
from app.repositories.ai_repository import AIRepository


def _build_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def test_camera_repository_respects_owner_scope():
    db = _build_session()
    try:
        owner = User(
            user_id=uuid.uuid4(),
            full_name="Owner",
            username="owner",
            email="owner@example.com",
            password_hash="hash",
        )
        other = User(
            user_id=uuid.uuid4(),
            full_name="Other",
            username="other",
            email="other@example.com",
            password_hash="hash",
        )
        owner_cam = Camera(
            camera_id=uuid.uuid4(),
            camera_name="Owner Cam",
            location="A",
            stream_url="rtsp://owner",
            camera_type="LIVE",
            owner_id=owner.user_id,
        )
        other_cam = Camera(
            camera_id=uuid.uuid4(),
            camera_name="Other Cam",
            location="B",
            stream_url="rtsp://other",
            camera_type="LIVE",
            owner_id=other.user_id,
        )
        db.add_all([owner, other, owner_cam, other_cam])
        db.commit()

        repo = CameraRepository(db)
        cam = repo.get_camera_for_user(owner_cam.camera_id, owner.user_id)
        assert cam is not None
        assert cam.camera_id == owner_cam.camera_id

        cam = repo.get_camera_for_user(other_cam.camera_id, owner.user_id)
        assert cam is None
    finally:
        db.close()


def test_ai_repository_filters_events_by_camera_owner():
    db = _build_session()
    try:
        owner = User(
            user_id=uuid.uuid4(),
            full_name="Owner",
            username="owner2",
            email="owner2@example.com",
            password_hash="hash",
        )
        other = User(
            user_id=uuid.uuid4(),
            full_name="Other",
            username="other2",
            email="other2@example.com",
            password_hash="hash",
        )
        owner_cam = Camera(
            camera_id=uuid.uuid4(),
            camera_name="Owner Cam",
            location="A",
            stream_url="rtsp://owner",
            camera_type="LIVE",
            owner_id=owner.user_id,
        )
        other_cam = Camera(
            camera_id=uuid.uuid4(),
            camera_name="Other Cam",
            location="B",
            stream_url="rtsp://other",
            camera_type="LIVE",
            owner_id=other.user_id,
        )
        owner_event = AIEvent(
            event_id=uuid.uuid4(),
            camera_id=owner_cam.camera_id,
            detected_by=owner.user_id,
            detection_type="Person",
            severity="High",
            confidence=0.9,
        )
        other_event = AIEvent(
            event_id=uuid.uuid4(),
            camera_id=other_cam.camera_id,
            detected_by=other.user_id,
            detection_type="Vehicle",
            severity="Medium",
            confidence=0.7,
        )
        db.add_all([owner, other, owner_cam, other_cam, owner_event, other_event])
        db.commit()

        repo = AIRepository(db)
        items = repo.list_events(owner_id=owner.user_id)
        assert len(items) == 1
        assert items[0].camera_id == owner_cam.camera_id
    finally:
        db.close()
