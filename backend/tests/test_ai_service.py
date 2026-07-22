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
            created_at=None,
            screenshot_path=None,
        )


def test_register_event_uses_none_for_invalid_track_id(monkeypatch):
    service = ai_service.AIService(db_session=object())
    fake_repo = FakeRepo()
    service.repo = fake_repo

    async def fake_broadcast(*args, **kwargs):
        return None

    monkeypatch.setattr(ai_service.manager, "broadcast", fake_broadcast)

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

    assert fake_repo.payloads[0]["track_id"] is None


def test_build_screenshot_filename_returns_human_readable_name():
    filename = ai_service.build_screenshot_filename(
        "Main Entrance",
        "LOITERING",
        datetime(2025, 1, 2, 15, 4, 5),
    )

    assert filename == "Main_Entrance_LOITERING_2025-01-02_15-04-05.jpg"
