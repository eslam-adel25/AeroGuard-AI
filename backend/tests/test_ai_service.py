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


def test_register_event_uses_none_for_invalid_track_id(monkeypatch):
    service = ai_service.AIService(db_session=object())
    fake_repo = FakeRepo()
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
    service = ai_service.AIService(db_session=object())
    fake_repo = FakeRepo()
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
