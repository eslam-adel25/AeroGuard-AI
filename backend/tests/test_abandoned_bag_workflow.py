import asyncio
import threading
import uuid
from types import SimpleNamespace

import numpy as np

from app.ai import processor as processor_module
from app.ai.processor import AIProcessor
from app.api.v1 import settings as settings_api
from app.models.models import Camera, RestrictedZone
from app.schemas.schemas import SettingsUpdate


def make_processor():
    processor = AIProcessor.__new__(AIProcessor)
    processor.abandoned_bag_runtime = {}
    processor.alert_persistence = {}
    processor.last_alert_time = {}
    return processor


def test_abandoned_bag_confirms_at_60_continuous_seconds_and_schedules_captures():
    processor = make_processor()

    before_threshold = processor._update_abandoned_bag_runtime(
        "camera-a", 42, 100.0, 159.999
    )
    confirmed = processor._update_abandoned_bag_runtime(
        "camera-a", 42, 100.0, 160.0
    )
    same_frame = processor._update_abandoned_bag_runtime(
        "camera-a", 42, 100.0, 160.0
    )
    before_five_seconds = processor._update_abandoned_bag_runtime(
        "camera-a", 42, 100.0, 164.999
    )
    five_seconds = processor._update_abandoned_bag_runtime(
        "camera-a", 42, 100.0, 165.0
    )

    assert before_threshold["confirmed"] is False
    assert confirmed["confirmed"] is True
    assert confirmed["newly_confirmed"] is True
    assert confirmed["capture"] is True
    assert same_frame["newly_confirmed"] is False
    assert same_frame["capture"] is False
    assert before_five_seconds["capture"] is False
    assert five_seconds["capture"] is True
    assert five_seconds["newly_confirmed"] is False


def test_owner_return_resets_timer_and_later_abandonment_starts_fresh():
    processor = make_processor()
    processor._update_abandoned_bag_runtime("camera-a", 42, 100.0, 130.0)

    returned = processor._update_abandoned_bag_runtime(
        "camera-a", 42, None, 140.0
    )
    assert returned["confirmed"] is False
    assert "42" not in processor.abandoned_bag_runtime.get("camera-a", {})

    later_pending = processor._update_abandoned_bag_runtime(
        "camera-a", 42, 150.0, 209.999
    )
    later_confirmed = processor._update_abandoned_bag_runtime(
        "camera-a", 42, 150.0, 210.0
    )

    assert later_pending["confirmed"] is False
    assert later_confirmed["newly_confirmed"] is True


def test_ownerless_bag_starts_on_first_detection_and_cancels_on_owner_candidate():
    processor = make_processor()
    first = processor._update_abandoned_bag_runtime(
        "camera-a",
        42,
        None,
        100.0,
        timer_origin="ownerless",
    )
    before_threshold = processor._update_abandoned_bag_runtime(
        "camera-a",
        42,
        None,
        159.999,
        timer_origin="ownerless",
    )
    cancelled = processor._update_abandoned_bag_runtime(
        "camera-a",
        42,
        None,
        160.0,
        timer_origin=None,
    )

    assert first["started_at"] == 100.0
    assert before_threshold["confirmed"] is False
    assert cancelled["confirmed"] is False
    assert "42" not in processor.abandoned_bag_runtime.get("camera-a", {})


def test_ownerless_bag_confirms_at_60_seconds_without_prior_owner():
    processor = make_processor()
    processor._update_abandoned_bag_runtime(
        "camera-a", 42, None, 100.0, timer_origin="ownerless"
    )

    pending = processor._update_abandoned_bag_runtime(
        "camera-a", 42, None, 159.999, timer_origin="ownerless"
    )
    confirmed = processor._update_abandoned_bag_runtime(
        "camera-a", 42, None, 160.0, timer_origin="ownerless"
    )

    assert pending["confirmed"] is False
    assert confirmed["confirmed"] is True
    assert confirmed["newly_confirmed"] is True
    assert confirmed["capture"] is True


def test_abandoned_bag_schedules_are_isolated_per_camera():
    processor = make_processor()

    processor._update_abandoned_bag_runtime("camera-a", 42, 100.0, 100.0)
    processor._update_abandoned_bag_runtime("camera-b", 42, 120.0, 120.0)
    camera_a = processor._update_abandoned_bag_runtime(
        "camera-a", 42, 100.0, 160.0
    )
    camera_b = processor._update_abandoned_bag_runtime(
        "camera-b", 42, 120.0, 160.0
    )

    assert camera_a["newly_confirmed"] is True
    assert camera_b["confirmed"] is False
    assert processor.abandoned_bag_runtime["camera-a"]["42"]["started_at"] == 100.0
    assert processor.abandoned_bag_runtime["camera-b"]["42"]["started_at"] == 120.0


def test_event_end_cleans_up_its_schedule():
    processor = make_processor()
    processor._update_abandoned_bag_runtime("camera-a", 42, 100.0, 160.0)

    ended = processor._update_abandoned_bag_runtime(
        "camera-a", 42, None, 161.0
    )

    assert ended["confirmed"] is False
    assert "camera-a" not in processor.abandoned_bag_runtime


def test_visible_bag_keeps_its_schedule_during_owner_state_cleanup():
    processor = make_processor()
    processor.bag_owner_state = {}
    processor.bag_owner_person_state = {}
    processor.bag_owner_evidence = {}
    processor.bag_owner_status = {}
    processor.abandoned_bag_runtime["camera-a"] = {
        "42": {
            "started_at": 100.0,
            "confirmed": False,
            "alert_key": "camera-a_42_ABANDONED",
            "last_capture_at": None,
        }
    }
    bag = SimpleNamespace(
        track_id=42,
        bbox=[20, 90, 60, 140],
        class_name="bag",
    )

    processor._assign_bag_owner("camera-a", [], [bag])

    assert "42" in processor.abandoned_bag_runtime["camera-a"]


def test_confirmed_visual_state_is_explicitly_red_and_danger():
    visual_state = AIProcessor._get_abandoned_bag_visual_state("Bag")

    assert visual_state == {
        "display_label": "ABANDONED_BAG",
        "status": "DANGER",
        "box_color": (0, 0, 255),
        "overlay_label": "Bag\nABANDONED",
    }


def test_settings_api_preserves_existing_abandoned_bag_threshold(monkeypatch):
    stored_settings = SimpleNamespace(
        abandoned_bag_enabled=True,
        abandoned_bag_seconds=20,
    )
    updates = []

    class SettingsRepo:
        def __init__(self, _db):
            pass

        def get_by_owner(self, _owner_id):
            return stored_settings

        def update(self, _owner_id, values):
            updates.append(values)
            for key, value in values.items():
                setattr(stored_settings, key, value)
            return stored_settings

    monkeypatch.setattr(settings_api, "SettingsRepository", SettingsRepo)
    monkeypatch.setattr(settings_api, "_ai_processor", None)

    read_settings = settings_api.get_current_settings(
        db=object(),
        current_user={"user_id": "owner-1"},
    )
    updated_settings = settings_api.update_settings(
        payload=SettingsUpdate(detection_confidence=0.73),
        db=object(),
        current_user={"user_id": "owner-1"},
    )

    assert read_settings["abandoned_bag_seconds"] == 20
    assert "abandoned_bag_seconds" not in updates[0]
    assert updated_settings["abandoned_bag_seconds"] == 20


def test_first_screenshot_is_immediate_then_recurs_every_five_seconds(monkeypatch):
    processor = make_processor()
    ticks = iter([0.0, 4.999, 5.0, 10.0])
    monkeypatch.setattr(
        processor_module,
        "time",
        SimpleNamespace(monotonic=lambda: next(ticks), time=lambda: 100.0),
    )

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

    class ScreenshotService:
        def __init__(self):
            self.registered = []
            self.attached = []

        def register_event(self, **kwargs):
            self.registered.append(kwargs)
            return SimpleNamespace(
                event_id=uuid.uuid4(),
                screenshot_path="first.jpg",
            )

        async def attach_screenshot(self, event_id, image_bytes):
            self.attached.append((event_id, image_bytes))

    service = ScreenshotService()
    active_keys = set()

    async def capture(frame, should_capture, immediate=False):
        await processor._register_persistent_alert(
            service,
            "camera-a",
            "camera-a_42_ABANDONED",
            "ABANDONED_BAG",
            "Critical",
            0.9,
            "42",
            "owner",
            {"bbox": [1, 2, 3, 4]},
            frame,
            active_keys,
            capture_screenshot=should_capture,
            capture_immediately=immediate,
        )

    asyncio.run(capture(b"first", True, immediate=True))
    asyncio.run(capture(b"frame-before-5s", False))
    asyncio.run(capture(b"second", True))
    asyncio.run(capture(b"third", True))

    assert len(service.registered) == 1
    assert service.registered[0]["screenshot_bytes"] == b"first"
    assert [image for _, image in service.attached] == [b"second", b"third"]


def test_ownerless_process_camera_publishes_red_frame_and_alarm_on_persistence_failure(
    monkeypatch,
):
    processor = AIProcessor.__new__(AIProcessor)
    processor._active_camera_lock = threading.Lock()
    processor._active_cameras = set()
    processor._starting_cameras = set()
    processor._camera_started_at = {}
    processor._last_frame_received_at = {}
    processor._stop_flags = {}
    processor._model_lock = threading.Lock()
    processor._settings_lock = threading.Lock()
    processor._settings_by_owner = {}
    processor.model_path = "test-model.pt"
    processor.fire_smoke_model = None
    processor.fire_smoke_class_map = {}
    processor.trackers = {}
    processor.object_history = {}
    processor.loitering_tracker = {}
    processor.bag_tracker = {}
    processor.display_id_state = {}
    processor.person_identity_registries = {}
    processor.bag_owner_state = {}
    processor.bag_owner_person_state = {}
    processor.bag_owner_evidence = {}
    processor.bag_owner_status = {}
    processor.abandoned_bag_runtime = {}
    processor.active_critical_alerts = {}
    processor.crowd_cooldown = {}
    processor._active_alarm_state = {}
    processor._active_alarm_sources = {}
    processor._active_tripwire_alarm_states = {}
    processor._deleted_tripwire_zones = set()
    processor.last_frames = {}
    processor.alert_persistence = {}
    processor.last_alert_time = {}
    processor._detection_persist_cooldown = {}
    processor.tripwire_runtime = {}

    camera = SimpleNamespace(
        camera_id="ownerless-camera",
        owner_id=None,
        customer_profile_id="tenant-a",
        status="Processing",
    )

    class Query:
        def __init__(self, model):
            self.model = model

        def filter(self, *_args):
            return self

        def exists(self):
            return True

        def all(self):
            return []

        def first(self):
            return camera if self.model is Camera else None

    class Database:
        def query(self, model):
            return Query(model)

        def commit(self):
            pass

        def rollback(self):
            pass

        def close(self):
            pass

    class Capture:
        def __init__(self):
            self.position = 0
            self.read_times = [100.0, 100.0, 160.0]

        def isOpened(self):
            return True

        def read(self):
            if self.position < len(self.read_times):
                clock.current = self.read_times[self.position]
                self.position += 1
                return True, np.zeros((100, 120, 3), dtype=np.uint8)
            return False, None

        def get(self, property_id):
            if property_id == processor_module.cv2.CAP_PROP_FRAME_COUNT:
                return 3
            if property_id == processor_module.cv2.CAP_PROP_POS_FRAMES:
                return self.position
            return 0

        def release(self):
            pass

    clock = SimpleNamespace(current=0.0)
    database = Database()
    capture = Capture()
    settings = SimpleNamespace(
        detection_confidence=0.5,
        max_objects=50,
        frame_skip=0,
        abandoned_bag_enabled=True,
        loitering_enabled=False,
        fire_detection_enabled=False,
        smoke_detection_enabled=False,
        restricted_area_enabled=False,
        wrong_direction_enabled=False,
    )
    broadcasts = []
    persist_attempts = []
    runtime_calls = []

    monkeypatch.setattr(processor_module, "SessionLocal", lambda: database)
    monkeypatch.setattr(
        processor_module.cv2,
        "VideoCapture",
        lambda *_args: capture,
    )
    monkeypatch.setattr(
        processor_module.time,
        "time",
        lambda: clock.current,
    )

    async def fail_persistence(*args, **kwargs):
        persist_attempts.append(kwargs)
        raise RuntimeError("simulated event persistence failure")

    async def record_broadcast(message, **_kwargs):
        broadcasts.append(message)

    monkeypatch.setattr(processor_module.manager, "broadcast", record_broadcast)
    processor._get_settings_for_owner = lambda *_args: settings
    processor._predict_frame = lambda *_args: ([], {})
    processor._extract_model_detections = lambda *_args: [
        {
            "bbox": [20, 20, 80, 80],
            "class_name": "bag",
            "confidence": 0.9,
        }
    ]

    update_runtime = processor._update_abandoned_bag_runtime

    def record_runtime_call(*args, **kwargs):
        runtime_calls.append((args, kwargs))
        return update_runtime(*args, **kwargs)

    processor._update_abandoned_bag_runtime = record_runtime_call
    processor._register_persistent_alert = fail_persistence
    processor._clear_camera_runtime_state = lambda *_args: None
    processor.reserve_camera_start("ownerless-camera")

    asyncio.run(
        processor.process_camera(
            "ownerless-camera",
            "archive.mp4",
            reserved=True,
        )
    )

    published_frame = processor.get_latest_frame("ownerless-camera")
    assert published_frame is not None
    assert len(runtime_calls) >= 2
    assert processor.abandoned_bag_runtime["ownerless-camera"]["1"]["started_at"] == 100.0
    assert processor.abandoned_bag_runtime["ownerless-camera"]["1"]["confirmed"]
    assert len(persist_attempts) == 1
    assert persist_attempts[0]["capture_screenshot"] is True
    assert persist_attempts[0]["capture_immediately"] is True
    assert tuple(int(channel) for channel in published_frame[20, 20]) == (0, 0, 255)
    active_alarm_updates = [
        message
        for message in broadcasts
        if message["event"] == "alarm_state" and message["data"]["active"]
    ]
    assert len(active_alarm_updates) == 1
    assert active_alarm_updates[0]["data"]["sources"] == ["ABANDONED_BAG"]
