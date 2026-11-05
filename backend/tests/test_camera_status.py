import asyncio
import threading
import time
import uuid
from datetime import date
from types import SimpleNamespace

import numpy as np
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi import BackgroundTasks
from sqlalchemy.orm.exc import DetachedInstanceError

from app.ai import processor as processor_module
from app.api.v1 import cameras as cameras_api
from app.api.v1 import reports as reports_api
from app.models.models import Base, Camera, User, UserSettings
from app.repositories.settings_repository import SettingsRepository
from app.services.camera_status import (
    CAMERA_NO_FRAME_GRACE_SECONDS,
    reconcile_orphaned_processing_statuses,
    resolve_camera_status,
)


def _create_processor():
    processor = processor_module.AIProcessor.__new__(
        processor_module.AIProcessor
    )
    processor._active_camera_lock = threading.Lock()
    processor._model_lock = threading.Lock()
    processor._active_cameras = set()
    processor._starting_cameras = set()
    processor._stop_flags = {}
    processor._camera_started_at = {}
    processor._last_frame_received_at = {}
    processor._settings_lock = threading.Lock()
    processor._settings_by_owner = {}
    processor.model_path = "test-model.pt"
    processor._active_alarm_state = {}
    processor._active_alarm_sources = {}
    processor._active_tripwire_alarm_states = {}
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
    processor.active_critical_alerts = {}
    processor.crowd_cooldown = {}
    processor.last_frames = {}
    processor._frame_states = {}
    processor._frame_states_lock = threading.Lock()
    processor.camera_pipelines = {}
    processor.live_frame_states = {}
    processor.live_frame_lock = threading.Lock()
    processor.ai_frame_buffers = {}
    processor.ai_frame_lock = threading.Lock()
    processor.alert_persistence = {}
    return processor


class _FakeQuery:
    def __init__(self, model, camera, settings_query_error=None):
        self.model = model
        self.camera = camera
        self.settings_query_error = settings_query_error

    def filter(self, *_args):
        return self

    def all(self):
        return []

    def first(self):
        if self.model is UserSettings and self.settings_query_error is not None:
            raise self.settings_query_error
        return self.camera if self.model is Camera else None


class _FakeDB:
    def __init__(self, camera, settings_query_error=None):
        self.camera = camera
        self.settings_query_error = settings_query_error
        self.commits = 0
        self.closed = False
        self.rollbacks = 0

    def query(self, model):
        return _FakeQuery(model, self.camera, self.settings_query_error)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed = True


class _FakeCapture:
    def __init__(self, opened=True, reads=None, block_on_read=False):
        self.opened = opened
        self.reads = list(reads or [])
        self.block_on_read = block_on_read
        self.read_started = threading.Event()
        self.read_released = threading.Event()
        self.release_count = 0
        self.read_count = 0

    def isOpened(self):
        return self.opened

    def open(self, *_args):
        return self.opened

    def read(self):
        self.read_started.set()
        self.read_count += 1
        if self.block_on_read:
            self.read_released.wait()
            return False, None
        if self.reads:
            return self.reads.pop(0)
        return False, None

    def get(self, _property):
        return 0

    def release(self):
        self.release_count += 1
        self.read_released.set()
        self.opened = False


def _processor_camera(db_camera, processor, monkeypatch, cap, events):
    camera = getattr(db_camera, "camera", None)
    if camera is not None and not getattr(camera, "customer_profile_id", None):
        camera.customer_profile_id = "tenant-a"
    monkeypatch.setattr(
        processor_module,
        "SessionLocal",
        lambda: db_camera,
    )
    monkeypatch.setattr(
        processor_module.cv2,
        "VideoCapture",
        lambda *_args: cap,
    )
    monkeypatch.setattr(
        processor,
        "_initialize_camera_runtime_state",
        lambda _camera_id: None,
    )
    monkeypatch.setattr(
        processor,
        "_clear_camera_runtime_state",
        lambda _camera_id: None,
    )

    async def broadcast(message, **_kwargs):
        events.append((message, db_camera.camera.status))

    monkeypatch.setattr(processor_module.manager, "broadcast", broadcast)


def test_status_resolver_requires_recent_frames_and_bounds_startup():
    now = 100.0
    runtime = {
        "cam-starting": {
            "started_at": now - CAMERA_NO_FRAME_GRACE_SECONDS + 1,
            "last_frame_at": None,
        },
        "cam-healthy": {
            "started_at": now - 20,
            "last_frame_at": now - 1,
        },
        "cam-stale": {
            "started_at": now - 20,
            "last_frame_at": now - CAMERA_NO_FRAME_GRACE_SECONDS - 1,
        },
    }

    assert resolve_camera_status("cam-starting", "Processing", runtime, now) == "Processing"
    assert resolve_camera_status("cam-healthy", "Processing", runtime, now) == "Running"
    assert resolve_camera_status("cam-stale", "Processing", runtime, now) == "Offline"
    assert resolve_camera_status("cam-orphan", "Processing", runtime, now) == "Offline"
    runtime["cam-stopping"] = {
        "started_at": now - 1,
        "last_frame_at": now,
        "stop_requested": True,
    }
    assert resolve_camera_status("cam-stopping", "Running", runtime, now) == "Offline"


def test_camera_list_and_report_dashboard_return_same_runtime_status(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    owner = User(
        user_id=uuid.uuid4(),
        full_name="Status Owner",
        username="status_owner",
        email="status_owner@example.com",
        password_hash="hash",
    )
    camera = Camera(
        camera_id=uuid.uuid4(),
        camera_name="Front Gate",
        location="Gate",
        stream_url="rtsp://camera/stream",
        camera_type="LIVE",
        status="Processing",
        owner_id=owner.user_id,
    )
    stale_camera = Camera(
        camera_id=uuid.uuid4(),
        camera_name="Stale Camera",
        location="Remote",
        stream_url="rtsp://stale/stream",
        camera_type="LIVE",
        status="Processing",
        owner_id=owner.user_id,
    )
    idle_camera = Camera(
        camera_id=uuid.uuid4(),
        camera_name="Idle Camera",
        location="Archive",
        stream_url="archive.mp4",
        camera_type="UPLOAD",
        status="Online",
        owner_id=owner.user_id,
    )
    session.add_all([owner, camera, stale_camera, idle_camera])
    session.commit()

    camera_key = str(camera.camera_id)
    frame_time = time.monotonic()

    class Runtime:
        def get_camera_runtime_statuses(self, camera_ids):
            return {
                camera_key: {
                    "started_at": frame_time - 2,
                    "last_frame_at": frame_time,
                }
                for camera_id in camera_ids
                if str(camera_id) == camera_key
            }

    monkeypatch.setattr(cameras_api, "ai_engine", Runtime())
    monkeypatch.setattr(reports_api, "ai_engine", Runtime())
    monkeypatch.setattr(
        reports_api.ReportService,
        "get_report_stats",
        lambda **_kwargs: {
            "summary": {"active_cameras": 0},
            "cameras": [
                {
                    "camera_id": camera_key,
                    "camera_name": camera.camera_name,
                    "location": camera.location,
                    "status": camera.status,
                },
                {
                    "camera_id": str(stale_camera.camera_id),
                    "camera_name": stale_camera.camera_name,
                    "location": stale_camera.location,
                    "status": stale_camera.status,
                },
                {
                    "camera_id": str(idle_camera.camera_id),
                    "camera_name": idle_camera.camera_name,
                    "location": idle_camera.location,
                    "status": idle_camera.status,
                },
            ],
            "charts": {
                "top_cameras": [
                    {
                        "camera_id": camera_key,
                        "camera_name": camera.camera_name,
                        "location": camera.location,
                        "status": camera.status,
                        "count": 1,
                    },
                    {
                        "camera_id": str(stale_camera.camera_id),
                        "camera_name": stale_camera.camera_name,
                        "location": stale_camera.location,
                        "status": stale_camera.status,
                        "count": 1,
                    },
                ]
            },
        },
    )

    try:
        list_response = cameras_api.get_cameras(
            session,
            {"user_id": owner.user_id, "role": "User"},
        )
        report_response = asyncio.run(
            reports_api.get_dashboard(
                start_date=date(2026, 1, 1),
                end_date=date(2026, 1, 2),
                camera_id=None,
                detection_type=None,
                severity=None,
                confidence_min=None,
                confidence_max=None,
                db=session,
                current_user={"user_id": owner.user_id, "role": "User"},
            )
        )

        list_statuses = {
            str(item.camera_id): item.status for item in list_response
        }
        report_statuses = {
            item["camera_id"]: item["status"]
            for item in report_response["cameras"]
        }
        top_statuses = {
            item["camera_id"]: item["status"]
            for item in report_response["charts"]["top_cameras"]
        }
        assert list_statuses[camera_key] == "Running"
        assert report_statuses[camera_key] == "Running"
        assert top_statuses[camera_key] == "Running"
        assert list_statuses[str(stale_camera.camera_id)] == "Offline"
        assert list_statuses[str(idle_camera.camera_id)] == "Online"
        assert report_statuses[str(stale_camera.camera_id)] == "Offline"
        assert report_statuses[str(idle_camera.camera_id)] == "Online"
        assert top_statuses[str(stale_camera.camera_id)] == "Offline"
        assert report_response["summary"]["active_cameras"] == 1
    finally:
        session.close()
        engine.dispose()


def test_closed_request_settings_snapshot_is_used_by_started_camera(
    monkeypatch,
):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SettingsSession = sessionmaker(bind=engine)
    settings_session = SettingsSession()
    owner_id = uuid.uuid4()
    owner = User(
        user_id=owner_id,
        full_name="Settings Owner",
        username="settings_owner",
        email="settings_owner@example.com",
        password_hash="hash",
    )
    settings = UserSettings(
        owner_id=owner_id,
        detection_confidence=0.73,
        max_objects=23,
        gpu_enabled=False,
        frame_skip=0,
    )
    settings_session.add_all([owner, settings])
    settings_session.commit()

    processor = _create_processor()
    monkeypatch.setattr(
        processor_module,
        "YOLO",
        lambda *_args, **_kwargs: SimpleNamespace(names={}),
    )
    processor.update_config(SettingsRepository(settings_session).get_by_owner(owner_id))
    settings_session.expire(settings)
    settings_session.close()
    with pytest.raises(DetachedInstanceError):
        _ = settings.detection_confidence

    camera = SimpleNamespace(
        camera_id="settings-camera",
        camera_name="Settings Camera",
        location="Test",
        camera_type="UPLOAD",
        stream_url="archive.mp4",
        owner_id=owner_id,
        status="Offline",
    )
    worker_db = _FakeDB(camera)
    cap = _FakeCapture(
        reads=[
            (True, np.zeros((2, 2, 3), dtype=np.uint8)),
            (False, None),
        ]
    )
    cap.get = lambda property_id: (
        1
        if property_id
        in {
            processor_module.cv2.CAP_PROP_FRAME_COUNT,
            processor_module.cv2.CAP_PROP_POS_FRAMES,
        }
        else 0
    )
    events = []
    _processor_camera(worker_db, processor, monkeypatch, cap, events)
    processor._predict_frame = lambda *_args: (
        processor_module._build_empty_model_result(),
        {},
    )

    class EmptyTracker:
        def update(self, _detections):
            return []

        def get_active_tracks(self):
            return []

    processor._initialize_camera_runtime_state = lambda camera_id: (
        processor.trackers.__setitem__(camera_id, EmptyTracker()),
        processor.bag_owner_status.__setitem__(camera_id, {}),
    )
    processor._assign_person_ids = lambda *_args: {}
    processor._assign_bag_owner = lambda *_args: {}

    monkeypatch.setattr(cameras_api, "ai_engine", processor)
    monkeypatch.setattr(
        cameras_api,
        "_get_camera_for_user",
        lambda *_args: camera,
    )

    async def start_camera():
        tasks = BackgroundTasks()
        response = await cameras_api.start_analysis(
            camera.camera_id,
            tasks,
            worker_db,
            {"user_id": owner_id, "role": "User"},
        )
        assert response["status"] == "started"
        assert len(tasks.tasks) == 1
        await tasks.tasks[0]()

    try:
        asyncio.run(start_camera())

        cached_settings = processor._settings_by_owner[str(owner_id)]
        assert not isinstance(cached_settings, UserSettings)
        assert cached_settings.detection_confidence == pytest.approx(0.73)
        assert cached_settings.max_objects == 23
        assert camera.status == "Offline"
        assert cap.release_count == 1
        assert any(
            message["event"] == "camera_status"
            and message["data"]["status"] == "Running"
            for message, _status in events
        )
    finally:
        settings_session.close()
        engine.dispose()


def test_settings_query_failure_releases_only_the_failing_camera(
    monkeypatch,
):
    camera = SimpleNamespace(
        camera_id="settings-failure",
        owner_id=uuid.uuid4(),
        status="Processing",
    )
    worker_db = _FakeDB(camera, settings_query_error=RuntimeError("db unavailable"))
    processor = _create_processor()
    cap = _FakeCapture()
    events = []
    _processor_camera(worker_db, processor, monkeypatch, cap, events)
    processor.reserve_camera_start(camera.camera_id)
    processor.reserve_camera_start("healthy-camera")

    asyncio.run(
        processor.process_camera(
            camera.camera_id,
            "archive.mp4",
            reserved=True,
        )
    )

    assert camera.status == "Offline"
    assert cap.release_count == 1
    assert camera.camera_id not in processor._active_cameras
    assert "healthy-camera" in processor._active_cameras
    assert processor._stop_flags["healthy-camera"] is False
    assert events[-1][0]["event"] == "camera_status"
    assert events[-1][0]["data"]["status"] == "Offline"


def test_startup_reconciliation_only_resets_persisted_processing():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    owner = User(
        user_id=uuid.uuid4(),
        full_name="Restart Owner",
        username="restart_owner",
        email="restart_owner@example.com",
        password_hash="hash",
    )
    processing = Camera(
        camera_id=uuid.uuid4(),
        camera_name="Stale Processing",
        location="A",
        stream_url="video.mp4",
        camera_type="UPLOAD",
        status="Processing",
        owner_id=owner.user_id,
    )
    online = Camera(
        camera_id=uuid.uuid4(),
        camera_name="Preserved Online",
        location="B",
        stream_url="0",
        camera_type="USB",
        status="Online",
        owner_id=owner.user_id,
    )
    session.add_all([owner, processing, online])
    session.commit()

    try:
        assert reconcile_orphaned_processing_statuses(session) == 1
        session.refresh(processing)
        session.refresh(online)
        assert processing.status == "Offline"
        assert online.status == "Online"
    finally:
        session.close()
        engine.dispose()


@pytest.mark.parametrize(
    ("camera_type", "source"),
    [
        ("LIVE", "rtsp://camera/stream"),
        ("UPLOAD", "archive.mp4"),
        ("USB", "0"),
    ],
)
def test_failed_capture_startup_persists_and_broadcasts_offline(
    camera_type,
    source,
    monkeypatch,
):
    camera = SimpleNamespace(
        camera_id=f"failed-{camera_type}",
        owner_id=None,
        status="Processing",
    )
    db = _FakeDB(camera)
    processor = _create_processor()
    cap = _FakeCapture(opened=False)
    events = []
    _processor_camera(db, processor, monkeypatch, cap, events)
    processor.reserve_camera_start(camera.camera_id)

    asyncio.run(
        processor.process_camera(
            camera.camera_id,
            source,
            reserved=True,
        )
    )

    assert camera.status == "Offline"
    assert cap.release_count == 1
    assert camera.camera_id not in processor._active_cameras
    assert [event[0]["data"]["status"] for event in events] == [
        "Processing",
        "Offline",
    ]
    assert events[-1][1] == "Offline"


@pytest.mark.parametrize("camera_type,source", [("LIVE", "rtsp://camera"), ("USB", "0")])
def test_live_capture_recovers_from_transient_read_failure_within_grace(
    camera_type,
    source,
    monkeypatch,
):
    del camera_type
    processor = _create_processor()
    cap = _FakeCapture(
        reads=[
            (False, None),
            (True, np.zeros((1, 1, 3), dtype=np.uint8)),
        ]
    )
    processor.reserve_camera_start("recovering")
    deadline = time.monotonic() + 1

    result = asyncio.run(
        processor._read_live_frame(cap, "recovering", deadline)
    )

    assert result is not None
    assert result[0] is True
    assert cap.read_count == 2
    assert cap.release_count == 0
    assert "recovering" in processor._active_cameras


def test_live_capture_accepts_read_delayed_beyond_250ms_within_grace():
    processor = _create_processor()
    cap = _FakeCapture()
    read_started = threading.Event()
    allow_read_to_finish = threading.Event()

    def delayed_read():
        cap.read_count += 1
        read_started.set()
        if not allow_read_to_finish.wait(timeout=2):
            return False, None
        return True, np.zeros((1, 1, 3), dtype=np.uint8)

    cap.read = delayed_read
    processor.reserve_camera_start("delayed")

    async def complete_delayed_read():
        read_task = asyncio.create_task(
            processor._read_live_frame(
                cap,
                "delayed",
                time.monotonic() + CAMERA_NO_FRAME_GRACE_SECONDS,
            )
        )
        while not read_started.is_set():
            await asyncio.sleep(0.01)
        await asyncio.sleep(0.35)
        allow_read_to_finish.set()
        return await read_task

    result = asyncio.run(complete_delayed_read())

    assert result is not None
    assert result[0] is True
    assert cap.read_count == 1
    assert cap.release_count == 0
    assert "delayed" in processor._active_cameras


def test_live_capture_no_frame_timeout_releases_capture(monkeypatch):
    processor = _create_processor()
    cap = _FakeCapture(block_on_read=True)
    processor.reserve_camera_start("blocked")

    async def read_with_timeout():
        started_at = time.monotonic()
        read_task = asyncio.create_task(
            processor._read_live_frame(
                cap,
                "blocked",
                time.monotonic() + 0.35,
            )
        )
        assert await asyncio.to_thread(cap.read_started.wait, 1)
        result = await read_task
        assert time.monotonic() - started_at >= 0.3
        return result

    result = asyncio.run(read_with_timeout())

    assert result is None
    assert cap.release_count == 1
    assert cap.read_released.is_set()


def test_live_capture_read_exception_releases_capture():
    processor = _create_processor()
    cap = _FakeCapture()
    cap.read = lambda: (_ for _ in ()).throw(RuntimeError("read failed"))
    processor.reserve_camera_start("read-error")

    frame_result = asyncio.run(
        processor._read_live_frame(
            cap,
            "read-error",
            time.monotonic() + 1,
        )
    )

    assert frame_result is None
    assert cap.release_count == 1


def test_delayed_live_read_does_not_affect_another_camera():
    processor = _create_processor()
    delayed_capture = _FakeCapture()
    read_started = threading.Event()
    allow_read_to_finish = threading.Event()
    processor.reserve_camera_start("delayed-camera")
    processor.reserve_camera_start("healthy-camera")
    processor._record_frame_received("healthy-camera")
    healthy_frame_at = processor.get_camera_runtime_statuses(
        ["healthy-camera"]
    )["healthy-camera"]["last_frame_at"]

    def delayed_read():
        delayed_capture.read_count += 1
        read_started.set()
        if not allow_read_to_finish.wait(timeout=2):
            return False, None
        return True, np.zeros((1, 1, 3), dtype=np.uint8)

    delayed_capture.read = delayed_read

    async def complete_delayed_read():
        read_task = asyncio.create_task(
            processor._read_live_frame(
                delayed_capture,
                "delayed-camera",
                time.monotonic() + CAMERA_NO_FRAME_GRACE_SECONDS,
            )
        )
        while not read_started.is_set():
            await asyncio.sleep(0.01)
        await asyncio.sleep(0.35)
        allow_read_to_finish.set()
        return await read_task

    result = asyncio.run(complete_delayed_read())
    statuses = processor.get_camera_runtime_statuses(
        ["delayed-camera", "healthy-camera"]
    )

    assert result is not None and result[0] is True
    assert delayed_capture.read_count == 1
    assert statuses["healthy-camera"]["last_frame_at"] == healthy_frame_at
    assert set(statuses) == {"delayed-camera", "healthy-camera"}


def test_no_frame_timeout_cleans_worker_and_persists_offline(monkeypatch):
    camera = SimpleNamespace(
        camera_id="no-frame-timeout",
        owner_id=None,
        status="Processing",
    )
    db = _FakeDB(camera)
    processor = _create_processor()
    cap = _FakeCapture(block_on_read=True)
    reconnect_capture = _FakeCapture(opened=False)
    events = []
    _processor_camera(db, processor, monkeypatch, cap, events)
    captures = iter((cap, reconnect_capture))
    monkeypatch.setattr(
        processor_module.cv2,
        "VideoCapture",
        lambda *_args: next(captures),
    )
    processor.reserve_camera_start(camera.camera_id)
    monkeypatch.setattr(
        processor_module,
        "CAMERA_NO_FRAME_GRACE_SECONDS",
        0.2,
    )

    async def wait_for_timeout():
        worker = asyncio.create_task(
            processor.process_camera(
                camera.camera_id,
                "rtsp://camera/stream",
                reserved=True,
            )
        )
        assert await asyncio.to_thread(cap.read_started.wait, 1)
        await asyncio.wait_for(worker, timeout=2)

    asyncio.run(wait_for_timeout())

    assert camera.status == "Offline"
    assert cap.release_count == 1
    assert reconnect_capture.release_count == 1
    assert camera.camera_id not in processor._active_cameras
    assert events[-1][0]["data"]["status"] == "Offline"
    assert events[-1][1] == "Offline"


def test_explicit_stop_preserves_source_until_source_shutdown(monkeypatch):
    camera = SimpleNamespace(
        camera_id="stopped",
        owner_id=None,
        status="Processing",
    )
    db = _FakeDB(camera)
    processor = _create_processor()
    cap = _FakeCapture(block_on_read=True)
    events = []
    _processor_camera(db, processor, monkeypatch, cap, events)
    processor.reserve_camera_start(camera.camera_id)

    async def stop_during_read():
        worker = asyncio.create_task(
            processor.process_camera(
                camera.camera_id,
                "rtsp://camera/stream",
                reserved=True,
            )
        )
        assert await asyncio.to_thread(cap.read_started.wait, 1)
        processor.stop_camera(camera.camera_id)
        await asyncio.wait_for(worker, timeout=2)

    asyncio.run(stop_during_read())

    assert camera.status == "Processing"
    assert cap.release_count == 0
    assert processor.has_active_camera_source(camera.camera_id)
    assert camera.camera_id not in processor._active_cameras
    assert events[-1][0]["data"]["status"] == "Processing"
    assert events[-1][1] == "Processing"
    processor.stop_camera_source(camera.camera_id)
    assert cap.release_count == 1
    assert not processor.has_active_camera_source(camera.camera_id)


def test_worker_cancellation_preserves_source_until_shutdown(monkeypatch):
    camera = SimpleNamespace(
        camera_id="shutdown-cancel",
        owner_id=None,
        status="Processing",
    )
    db = _FakeDB(camera)
    processor = _create_processor()
    cap = _FakeCapture(block_on_read=True)
    events = []
    _processor_camera(db, processor, monkeypatch, cap, events)
    processor.reserve_camera_start(camera.camera_id)

    async def cancel_worker():
        worker = asyncio.create_task(
            processor.process_camera(
                camera.camera_id,
                "rtsp://camera/stream",
                reserved=True,
            )
        )
        assert await asyncio.to_thread(cap.read_started.wait, 1)
        worker.cancel()
        with pytest.raises(asyncio.CancelledError):
            await worker

    asyncio.run(cancel_worker())

    assert camera.status == "Processing"
    assert cap.release_count == 0
    assert processor.has_active_camera_source(camera.camera_id)
    assert camera.camera_id not in processor._active_cameras
    assert events[-1][0]["data"]["status"] == "Processing"
    assert events[-1][1] == "Processing"
    processor.stop_camera_source(camera.camera_id)
    assert cap.release_count == 1
    assert not processor.has_active_camera_source(camera.camera_id)


def test_unexpected_capture_exception_cleans_only_its_camera(monkeypatch):
    camera = SimpleNamespace(
        camera_id="broken",
        owner_id=None,
        status="Processing",
    )
    other_camera_id = "healthy"
    db = _FakeDB(camera)
    processor = _create_processor()
    cap = _FakeCapture()
    cap.read = lambda: (_ for _ in ()).throw(RuntimeError("read failed"))
    events = []
    _processor_camera(db, processor, monkeypatch, cap, events)
    processor.reserve_camera_start(camera.camera_id)
    processor.reserve_camera_start(other_camera_id)
    processor._record_frame_received(other_camera_id)

    asyncio.run(
        processor.process_camera(
            camera.camera_id,
            "rtsp://camera/stream",
            reserved=True,
        )
    )

    assert camera.status == "Offline"
    assert camera.camera_id not in processor._active_cameras
    assert other_camera_id in processor._active_cameras
    assert processor._stop_flags[other_camera_id] is False
    assert events[-1][0]["data"]["status"] == "Offline"
    assert processor.get_camera_runtime_statuses([other_camera_id])[
        other_camera_id
    ]["last_frame_at"] is not None


def test_file_eof_still_finishes_offline(monkeypatch):
    camera = SimpleNamespace(
        camera_id="file-eof",
        owner_id=None,
        status="Processing",
    )
    db = _FakeDB(camera)
    processor = _create_processor()
    cap = _FakeCapture(reads=[(False, None)])

    def get_frame_metadata(property_id):
        if property_id == processor_module.cv2.CAP_PROP_FRAME_COUNT:
            return 10
        if property_id == processor_module.cv2.CAP_PROP_POS_FRAMES:
            return 10
        return 0

    cap.get = get_frame_metadata
    events = []
    _processor_camera(db, processor, monkeypatch, cap, events)
    processor.reserve_camera_start(camera.camera_id)

    asyncio.run(
        processor.process_camera(
            camera.camera_id,
            "archive.mp4",
            reserved=True,
        )
    )

    assert camera.status == "Offline"
    assert cap.read_count == 1
    assert cap.release_count == 1
    assert events[-1][0]["data"]["status"] == "Offline"
