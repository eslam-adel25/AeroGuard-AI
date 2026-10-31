import asyncio
import uuid
from datetime import datetime
from types import SimpleNamespace

from app.services import ai_service


class FakeRepo:
    def __init__(self):
        self.payloads = []

    def create_event(self, payload):
        self.payloads.append(payload)
        return SimpleNamespace(
            event_id=uuid.uuid4(),
            camera_id=payload.get("camera_id"),
            detection_type=payload.get("detection_type"),
            severity=payload.get("severity"),
            confidence=payload.get("confidence"),
            created_at=datetime.now(),
            screenshot_path=payload.get("screenshot_path"),
        )


class FakeCameraQuery:
    def filter(self, *_args):
        return self

    def first(self):
        return SimpleNamespace(
            camera_id="cam-1",
            camera_name="Test camera",
            owner_id="owner-1",
            customer_profile_id="tenant-a",
        )


class FakeDB:
    def query(self, _model):
        return FakeCameraQuery()


def test_register_event_uses_none_for_invalid_track_id(monkeypatch):
    service = ai_service.AIService(db_session=FakeDB())
    fake_repo = FakeRepo()
    fake_repo.db = service.repo.db
    service.repo = fake_repo

    async def fake_broadcast(*args, **kwargs):
        return None

    monkeypatch.setattr(ai_service.manager, "broadcast", fake_broadcast)

    async def create_event():
        service.register_event(
            camera_id="cam-1",
            detection_type="LOITERING",
            severity="High",
            confidence=0.8,
            track_id="not-a-uuid",
            user_id=None,
            owner_id="owner-1",
            metadata={"bbox": [1, 2, 3, 4]},
            screenshot_bytes=None,
        )
        await asyncio.sleep(0)

    asyncio.run(create_event())

    assert fake_repo.payloads[0]["track_id"] is None


def test_build_screenshot_filename_returns_human_readable_name():
    filename = ai_service.build_screenshot_filename(
        "Main Entrance",
        "LOITERING",
        datetime(2025, 1, 2, 15, 4, 5),
    )

    assert filename == "Main_Entrance_LOITERING_2025-01-02_15-04-05.jpg"


def test_event_broadcast_does_not_depend_on_screenshot_persistence(monkeypatch):
    service = ai_service.AIService(db_session=FakeDB())
    fake_repo = FakeRepo()
    fake_repo.db = service.repo.db
    service.repo = fake_repo
    messages = []

    async def fake_broadcast(message, **_kwargs):
        messages.append(message)

    monkeypatch.setattr(ai_service.manager, "broadcast", fake_broadcast)

    async def create_eligible_event():
        event = service.register_event(
            camera_id="cam-1",
            detection_type="LOITERING",
            severity="High",
            confidence=0.8,
            user_id=None,
            owner_id="owner-1",
            metadata={},
            screenshot_bytes=None,
        )
        await asyncio.sleep(0)
        return event

    event = asyncio.run(create_eligible_event())

    assert event.screenshot_path is None
    assert len(messages) == 1
    assert messages[0]["event"] == "ai_event"
    assert messages[0]["data"]["event_id"] == str(event.event_id)


def test_attach_screenshot_persists_all_paths_on_one_event(monkeypatch):
    event = SimpleNamespace(
        event_id=uuid.uuid4(),
        camera_id="cam-1",
        detection_type="ABANDONED_BAG",
        severity="Critical",
        confidence=0.9,
        created_at=datetime.now(),
        screenshot_path="first.jpg",
        event_metadata={"bbox": [1, 2, 3, 4]},
        detected_by="owner-1",
    )

    class ScreenshotRepo:
        def get_event(self, _event_id):
            return event

        def update_event(self, _event_id, **kwargs):
            for key, value in kwargs.items():
                setattr(event, key, value)
            return event

    service = ai_service.AIService(db_session=object())
    service.repo = ScreenshotRepo()
    saved_paths = iter(["second.jpg", "third.jpg"])
    monkeypatch.setattr(
        service,
        "_save_screenshot",
        lambda *_args, **_kwargs: next(saved_paths),
    )
    messages = []

    async def fake_broadcast(*_args, **_kwargs):
        messages.append(_args)

    monkeypatch.setattr(ai_service.manager, "broadcast", fake_broadcast)

    async def attach_both():
        await service.attach_screenshot(str(event.event_id), b"second")
        await service.attach_screenshot(str(event.event_id), b"third")

    asyncio.run(attach_both())

    assert event.screenshot_path == "third.jpg"
    assert event.event_metadata["screenshot_paths"] == [
        "first.jpg",
        "second.jpg",
        "third.jpg",
    ]
    assert messages == []
