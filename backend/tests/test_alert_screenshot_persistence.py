import asyncio
import time as time_module
import uuid
from types import SimpleNamespace

from app.ai import processor as processor_module


class FakeScreenshotService:
    def __init__(self):
        self.events = []
        self.attachments = []

    def register_event(self, **kwargs):
        event = SimpleNamespace(
            event_id=uuid.uuid4(),
            screenshot_path=None,
        )
        self.events.append((event, kwargs))
        return event

    async def attach_screenshot(self, event_id, image_bytes):
        self.attachments.append((event_id, image_bytes))
        return SimpleNamespace(screenshot_path="stored/path.jpg")


def make_processor(monkeypatch, clock, wall_clock=None):
    processor = processor_module.AIProcessor.__new__(processor_module.AIProcessor)
    processor.alert_persistence = {}
    processor.last_alert_time = {}
    wall_clock = wall_clock or iter([time_module.time()] * 20)

    async def fake_broadcast(_message):
        return None

    monkeypatch.setattr(processor_module.manager, "broadcast", fake_broadcast)
    monkeypatch.setattr(
        processor_module,
        "time",
        SimpleNamespace(
            monotonic=lambda: next(clock),
            time=lambda: next(wall_clock),
        ),
    )
    return processor


def patch_encoder(monkeypatch):
    class EncodedFrame:
        def __init__(self, frame):
            self.frame = frame

        def tobytes(self):
            return self.frame

    monkeypatch.setattr(
        processor_module.cv2,
        "imencode",
        lambda _extension, frame: (True, EncodedFrame(frame)),
    )


def run_alert(processor, service, active_keys, frame, alert_key="camera-object-alert"):
    asyncio.run(
        processor._register_persistent_alert(
            service,
            "camera",
            alert_key,
            "RESTRICTED AREA",
            "Critical",
            0.9,
            "object",
            "owner",
            {"bbox": [1, 2, 3, 4]},
            frame,
            active_keys,
            capture_screenshot=True,
        )
    )


def test_short_alert_does_not_capture(monkeypatch):
    patch_encoder(monkeypatch)
    processor = make_processor(monkeypatch, iter([0, 3]))
    service = FakeScreenshotService()
    active_keys = set()

    run_alert(processor, service, active_keys, b"first")
    active_keys.clear()
    run_alert(processor, service, active_keys, b"current")

    assert service.attachments == []


def test_five_seconds_captures_current_frame_once(monkeypatch):
    patch_encoder(monkeypatch)
    processor = make_processor(monkeypatch, iter([0, 5, 10]))
    service = FakeScreenshotService()
    active_keys = set()

    run_alert(processor, service, active_keys, b"first")
    run_alert(processor, service, active_keys, b"confirmed")
    run_alert(processor, service, active_keys, b"later")

    assert service.attachments == [
        (str(service.events[0][0].event_id), b"confirmed"),
    ]


def test_alert_reset_starts_new_persistence_window(monkeypatch):
    patch_encoder(monkeypatch)
    processor = make_processor(
        monkeypatch,
        iter([0, 4]),
        iter([100, 100, 106, 106]),
    )
    service = FakeScreenshotService()
    active_keys = set()

    run_alert(processor, service, active_keys, b"first", "camera_object_alert")
    processor._reset_inactive_alert_persistence("camera", set())
    run_alert(processor, service, active_keys, b"returned", "camera_object_alert")

    assert len(service.events) == 2
    assert service.attachments == []


def test_alert_identities_are_independent(monkeypatch):
    patch_encoder(monkeypatch)
    processor = make_processor(monkeypatch, iter([0, 0, 5, 5]))
    service = FakeScreenshotService()
    first_keys = set()
    second_keys = set()

    run_alert(processor, service, first_keys, b"first", "camera-first")
    run_alert(processor, service, second_keys, b"second", "camera-second")
    run_alert(processor, service, first_keys, b"first-confirmed", "camera-first")
    run_alert(processor, service, second_keys, b"second-confirmed", "camera-second")

    assert [attachment[1] for attachment in service.attachments] == [
        b"first-confirmed",
        b"second-confirmed",
    ]