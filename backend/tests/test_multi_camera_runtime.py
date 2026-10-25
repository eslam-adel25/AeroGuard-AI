import asyncio
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Lock, Event, Thread
from time import sleep
from types import SimpleNamespace

import pytest
from fastapi import BackgroundTasks, HTTPException

from app.ai import processor as processor_module
from app.api.v1 import cameras as cameras_api
from app.api.v1 import websocket_api


def _processor_state():
    processor = processor_module.AIProcessor.__new__(
        processor_module.AIProcessor
    )
    processor._active_camera_lock = Lock()
    processor._active_cameras = set()
    processor._starting_cameras = set()
    processor._camera_started_at = {}
    processor._last_frame_received_at = {}
    processor._stop_flags = {}
    processor._model_lock = Lock()
    processor._settings_lock = Lock()
    processor._settings_by_owner = {}
    processor.model_path = "test-model.pt"
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
    return processor


def test_camera_runtime_state_is_distinct_and_cleaned_independently():
    processor = _processor_state()

    processor._initialize_camera_runtime_state("camera-a")
    processor._initialize_camera_runtime_state("camera-b")
    processor.abandoned_bag_runtime["camera-a"][1] = {
        "started_at": 0,
        "confirmed": False,
        "alert_key": "camera-a_1_ABANDONED",
        "last_capture_at": None,
    }
    processor.abandoned_bag_runtime["camera-b"][1] = {
        "started_at": 0,
        "confirmed": False,
        "alert_key": "camera-b_1_ABANDONED",
        "last_capture_at": None,
    }
    detection = {
        "bbox": [0, 0, 20, 20],
        "class_name": "person",
        "confidence": 0.9,
    }
    track_a = processor.trackers["camera-a"].update([detection])[0]
    track_b = processor.trackers["camera-b"].update([detection])[0]
    processor.object_history["camera-a"][track_a.track_id] = (10, 20)
    processor.object_history["camera-b"][track_b.track_id] = (80, 90)

    assert track_a.track_id == track_b.track_id
    assert processor.trackers["camera-a"] is not processor.trackers["camera-b"]
    assert processor.object_history["camera-a"] != processor.object_history["camera-b"]

    processor._clear_camera_runtime_state("camera-b")

    assert "camera-b" not in processor.trackers
    assert "camera-b" not in processor.object_history
    assert "camera-b" not in processor.abandoned_bag_runtime
    assert "camera-a" in processor.trackers
    assert processor.object_history["camera-a"] == {track_a.track_id: (10, 20)}
    assert 1 in processor.abandoned_bag_runtime["camera-a"]


def test_camera_start_reservation_and_stop_are_scoped_per_camera():
    processor = _processor_state()

    assert processor.reserve_camera_start("camera-a") == "reserved"
    assert processor.reserve_camera_start("camera-b") == "reserved"
    assert processor.reserve_camera_start("camera-a") == "active"

    processor.stop_camera("camera-b")

    assert processor._stop_flags == {"camera-a": False, "camera-b": True}
    assert processor.reserve_camera_start("camera-b") == "stopping"
    assert processor.reserve_camera_start("camera-a") == "active"

    processor.release_camera_start("camera-b")
    assert processor.reserve_camera_start("camera-b") == "reserved"


def test_concurrent_start_reservations_create_one_owner():
    processor = _processor_state()

    with ThreadPoolExecutor(max_workers=8) as pool:
        outcomes = list(pool.map(processor.reserve_camera_start, ["same-camera"] * 16))

    assert outcomes.count("reserved") == 1
    assert outcomes.count("active") == 15
    assert processor._active_cameras == {"same-camera"}


def test_concurrent_start_and_stop_leave_a_consistent_camera_state():
    processor = _processor_state()
    rendezvous = Barrier(3)

    def start_camera():
        rendezvous.wait()
        return processor.reserve_camera_start("camera")

    def stop_camera():
        rendezvous.wait()
        processor.stop_camera("camera")

    with ThreadPoolExecutor(max_workers=2) as pool:
        start_future = pool.submit(start_camera)
        stop_future = pool.submit(stop_camera)
        rendezvous.wait()
        start_result = start_future.result()
        stop_future.result()

    assert start_result == "reserved"
    assert processor._active_cameras == {"camera"}
    assert processor._stop_flags["camera"] in {False, True}


def test_failed_camera_setup_releases_only_its_reservation(monkeypatch):
    processor = _processor_state()
    processor.reserve_camera_start("camera-a")
    processor.reserve_camera_start("camera-b")

    def fail_session():
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(processor_module, "SessionLocal", fail_session)

    async def fake_broadcast(_message):
        return None

    monkeypatch.setattr(processor_module.manager, "broadcast", fake_broadcast)
    asyncio.run(
        processor.process_camera(
            "camera-a",
            "unused-source",
            reserved=True,
        )
    )

    assert "camera-a" not in processor._active_cameras
    assert "camera-a" not in processor._stop_flags
    assert "camera-b" in processor._active_cameras
    assert processor._stop_flags["camera-b"] is False


def test_camera_settings_updates_remain_owner_scoped(monkeypatch):
    processor = _processor_state()
    monkeypatch.setattr(
        processor_module,
        "YOLO",
        lambda *_args, **_kwargs: SimpleNamespace(names={}),
    )

    settings_a = SimpleNamespace(
        owner_id="owner-a",
        detection_confidence=0.2,
        gpu_enabled=False,
    )
    settings_b = SimpleNamespace(
        owner_id="owner-b",
        detection_confidence=0.8,
        gpu_enabled=False,
    )

    processor.update_config(settings_a)
    processor.update_config(settings_b)

    assert (
        processor._get_settings_for_owner("owner-a").detection_confidence
        == 0.2
    )
    assert (
        processor._get_settings_for_owner("owner-b").detection_confidence
        == 0.8
    )


def test_model_replacement_waits_for_inference_lock(monkeypatch):
    processor = _processor_state()
    old_model = SimpleNamespace(
        names={},
        predict=lambda *_args, **_kwargs: ["old-model-result"],
    )
    replacement = SimpleNamespace(names={})
    processor.model = old_model
    reload_entered = Event()
    reload_finished = Event()

    def fake_yolo(*_args, **_kwargs):
        reload_entered.set()
        return replacement

    monkeypatch.setattr(processor_module, "YOLO", fake_yolo)
    processor._model_lock.acquire()
    reload_thread = Thread(
        target=lambda: (
            processor.update_config(
                SimpleNamespace(
                    owner_id="owner",
                    detection_confidence=0.5,
                    gpu_enabled=False,
                )
            ),
            reload_finished.set(),
        )
    )
    reload_thread.start()

    try:
        assert not reload_entered.wait(timeout=0.05)
        assert not reload_finished.is_set()
    finally:
        processor._model_lock.release()
        reload_thread.join(timeout=2)

    assert reload_finished.is_set()
    assert processor.model is replacement


def test_concurrent_camera_predictions_are_serialized_and_keep_results_local():
    processor = _processor_state()
    state_lock = Lock()
    active_predictions = 0
    maximum_concurrent_predictions = 0

    class FakeModel:
        names = {0: "person"}

        def predict(self, frame, **_kwargs):
            nonlocal active_predictions, maximum_concurrent_predictions
            with state_lock:
                active_predictions += 1
                maximum_concurrent_predictions = max(
                    maximum_concurrent_predictions,
                    active_predictions,
                )
            sleep(0.02)
            with state_lock:
                active_predictions -= 1
            return [frame]

    processor.model = FakeModel()

    with ThreadPoolExecutor(max_workers=2) as pool:
        future_a = pool.submit(processor._predict_frame, "frame-a", 0.3)
        future_b = pool.submit(processor._predict_frame, "frame-b", 0.7)
        result_a, names_a = future_a.result()
        result_b, names_b = future_b.result()

    assert maximum_concurrent_predictions == 1
    assert result_a == ["frame-a"]
    assert result_b == ["frame-b"]
    assert names_a is processor.model.names
    assert names_b is processor.model.names


def test_camera_start_endpoint_keeps_other_camera_active(monkeypatch):
    processor = _processor_state()

    async def process_camera(*_args, **_kwargs):
        return None

    processor.process_camera = process_camera
    cameras = {
        camera_id: SimpleNamespace(
            camera_id=camera_id,
            camera_type="UPLOAD",
            stream_url=f"{camera_id}.mp4",
            status="Offline",
        )
        for camera_id in ("camera-a", "camera-b")
    }
    monkeypatch.setattr(cameras_api, "ai_engine", processor)
    monkeypatch.setattr(
        cameras_api,
        "_get_camera_for_user",
        lambda _db, camera_id, _user: cameras[camera_id],
    )

    class FakeDB:
        def commit(self):
            pass

    background_tasks = BackgroundTasks()

    async def start_both():
        first = await cameras_api.start_analysis(
            "camera-a",
            background_tasks,
            FakeDB(),
            {"user_id": "owner", "role": "User"},
        )
        second = await cameras_api.start_analysis(
            "camera-b",
            background_tasks,
            FakeDB(),
            {"user_id": "owner", "role": "User"},
        )
        duplicate = await cameras_api.start_analysis(
            "camera-a",
            background_tasks,
            FakeDB(),
            {"user_id": "owner", "role": "User"},
        )
        return first, second, duplicate

    first, second, duplicate = asyncio.run(start_both())

    assert first["status"] == second["status"] == duplicate["status"] == "started"
    assert processor._active_cameras == {"camera-a", "camera-b"}
    assert len(background_tasks.tasks) == 2


def test_camera_start_scheduling_failure_persists_offline(monkeypatch):
    processor = _processor_state()
    camera = SimpleNamespace(
        camera_id="camera-a",
        camera_type="UPLOAD",
        stream_url="camera-a.mp4",
        status="Offline",
    )
    monkeypatch.setattr(cameras_api, "ai_engine", processor)
    monkeypatch.setattr(
        cameras_api,
        "_get_camera_for_user",
        lambda _db, _camera_id, _user: camera,
    )

    class FakeDB:
        def __init__(self):
            self.commits = 0

        def commit(self):
            self.commits += 1

    class FailedBackgroundTasks(BackgroundTasks):
        def add_task(self, *_args, **_kwargs):
            raise RuntimeError("task scheduling failed")

    db = FakeDB()

    async def start():
        with pytest.raises(RuntimeError, match="task scheduling failed"):
            await cameras_api.start_analysis(
                camera.camera_id,
                FailedBackgroundTasks(),
                db,
                {"user_id": "owner", "role": "User"},
            )

    asyncio.run(start())

    assert camera.status == "Offline"
    assert db.commits == 2
    assert camera.camera_id not in processor._active_cameras
    assert camera.camera_id not in processor._stop_flags


def test_live_camera_stop_during_validation_cancels_start_without_affecting_other_camera(monkeypatch):
    processor = _processor_state()
    processor.reserve_camera_start("camera-b")
    validation_entered = asyncio.Event()
    allow_validation_to_finish = asyncio.Event()

    async def pause_validation(_url):
        validation_entered.set()
        await allow_validation_to_finish.wait()

    camera = SimpleNamespace(
        camera_id="camera-a",
        camera_type="LIVE",
        stream_url="rtsp://camera-a/stream",
        status="Offline",
    )
    monkeypatch.setattr(cameras_api, "ai_engine", processor)
    monkeypatch.setattr(
        cameras_api,
        "_get_camera_for_user",
        lambda _db, _camera_id, _user: camera,
    )
    monkeypatch.setattr(cameras_api, "_validate_live_rtsp_url", lambda url: url)
    monkeypatch.setattr(cameras_api, "_verify_live_rtsp", pause_validation)

    class FakeDB:
        def commit(self):
            pass

    class FakeCameraRepository:
        def __init__(self, _db):
            pass

        def get_all_cameras(self, **_kwargs):
            return [camera]

    class FakeCameraResponse:
        @classmethod
        def model_validate(cls, camera_record):
            return SimpleNamespace(
                camera_id=camera_record.camera_id,
                status=camera_record.status,
            )

    monkeypatch.setattr(cameras_api, "CameraRepository", FakeCameraRepository)
    monkeypatch.setattr(cameras_api, "CameraResponse", FakeCameraResponse)

    async def exercise_race():
        background_tasks = BackgroundTasks()
        user = {"user_id": "owner", "role": "User"}
        start_task = asyncio.create_task(
            cameras_api.start_analysis(
                "camera-a",
                background_tasks,
                FakeDB(),
                user,
            )
        )
        await validation_entered.wait()

        assert "camera-a" in processor._starting_cameras
        assert "camera-a" not in processor._active_cameras
        assert cameras_api.get_cameras(
            FakeDB(),
            user,
        )[0].status == "Offline"
        with pytest.raises(HTTPException) as duplicate_error:
            await cameras_api.start_analysis(
                "camera-a",
                background_tasks,
                FakeDB(),
                user,
            )
        assert duplicate_error.value.status_code == 409
        assert not background_tasks.tasks

        await cameras_api.stop_analysis(
            "camera-a",
            FakeDB(),
            user,
        )
        assert processor._stop_flags["camera-a"] is True
        assert camera.status == "Offline"
        assert "camera-b" in processor._active_cameras
        assert processor._stop_flags["camera-b"] is False

        allow_validation_to_finish.set()
        with pytest.raises(HTTPException) as cancelled_error:
            await start_task
        assert cancelled_error.value.status_code == 409
        assert not background_tasks.tasks
        assert "camera-a" not in processor._starting_cameras
        assert "camera-a" not in processor._active_cameras
        assert "camera-a" not in processor._stop_flags
        assert camera.status == "Offline"
        assert "camera-b" in processor._active_cameras
        assert processor._stop_flags["camera-b"] is False

    asyncio.run(exercise_race())


def test_live_camera_validation_failure_releases_startup_for_retry(monkeypatch):
    processor = _processor_state()
    camera = SimpleNamespace(
        camera_id="camera-a",
        camera_type="LIVE",
        stream_url="rtsp://camera-a/stream",
        status="Offline",
    )
    monkeypatch.setattr(cameras_api, "ai_engine", processor)
    monkeypatch.setattr(
        cameras_api,
        "_get_camera_for_user",
        lambda _db, _camera_id, _user: camera,
    )
    monkeypatch.setattr(cameras_api, "_validate_live_rtsp_url", lambda url: url)

    class FakeDB:
        def commit(self):
            pass

    async def exercise_retry():
        failed_tasks = BackgroundTasks()

        async def fail_validation(_url):
            raise HTTPException(status_code=400, detail="invalid stream")

        monkeypatch.setattr(cameras_api, "_verify_live_rtsp", fail_validation)
        with pytest.raises(HTTPException) as validation_error:
            await cameras_api.start_analysis(
                "camera-a",
                failed_tasks,
                FakeDB(),
                {"user_id": "owner", "role": "User"},
            )
        assert validation_error.value.status_code == 400
        assert not failed_tasks.tasks
        assert "camera-a" not in processor._starting_cameras
        assert "camera-a" not in processor._active_cameras
        assert "camera-a" not in processor._stop_flags
        assert camera.status == "Offline"

        async def pass_validation(_url):
            return None

        monkeypatch.setattr(cameras_api, "_verify_live_rtsp", pass_validation)
        retry_tasks = BackgroundTasks()
        response = await cameras_api.start_analysis(
            "camera-a",
            retry_tasks,
            FakeDB(),
            {"user_id": "owner", "role": "User"},
        )
        assert response == {"status": "started", "camera_id": "camera-a"}
        assert len(retry_tasks.tasks) == 1
        assert "camera-a" in processor._active_cameras
        assert "camera-a" not in processor._starting_cameras

    asyncio.run(exercise_retry())


def test_cancelled_live_camera_start_releases_only_its_pending_reservation(monkeypatch):
    processor = _processor_state()
    assert processor.reserve_camera_start("camera-b") == "reserved"
    validation_entered = asyncio.Event()

    async def pause_validation(_url):
        validation_entered.set()
        await asyncio.Event().wait()

    camera = SimpleNamespace(
        camera_id="camera-a",
        camera_type="LIVE",
        stream_url="rtsp://camera-a/stream",
        status="Offline",
    )
    monkeypatch.setattr(cameras_api, "ai_engine", processor)
    monkeypatch.setattr(
        cameras_api,
        "_get_camera_for_user",
        lambda _db, _camera_id, _user: camera,
    )
    monkeypatch.setattr(cameras_api, "_validate_live_rtsp_url", lambda url: url)
    monkeypatch.setattr(cameras_api, "_verify_live_rtsp", pause_validation)

    class FakeDB:
        def commit(self):
            pass

    async def exercise_cancellation_and_retry():
        background_tasks = BackgroundTasks()
        user = {"user_id": "owner", "role": "User"}
        start_task = asyncio.create_task(
            cameras_api.start_analysis(
                "camera-a",
                background_tasks,
                FakeDB(),
                user,
            )
        )
        await validation_entered.wait()
        assert "camera-a" in processor._starting_cameras
        assert "camera-a" not in processor._active_cameras

        start_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await start_task

        assert "camera-a" not in processor._starting_cameras
        assert "camera-a" not in processor._active_cameras
        assert "camera-a" not in processor._stop_flags
        assert not background_tasks.tasks
        assert processor._active_cameras == {"camera-b"}
        assert processor._stop_flags["camera-b"] is False

        async def pass_validation(_url):
            return None

        monkeypatch.setattr(cameras_api, "_verify_live_rtsp", pass_validation)
        retry_tasks = BackgroundTasks()
        response = await cameras_api.start_analysis(
            "camera-a",
            retry_tasks,
            FakeDB(),
            user,
        )
        assert response == {"status": "started", "camera_id": "camera-a"}
        assert len(retry_tasks.tasks) == 1
        assert processor._active_cameras == {"camera-a", "camera-b"}
        assert "camera-a" not in processor._starting_cameras
        assert processor._stop_flags["camera-b"] is False

    asyncio.run(exercise_cancellation_and_retry())


def test_alarm_snapshot_contains_only_authorized_camera_state(monkeypatch):
    camera_a = SimpleNamespace(camera_id="camera-a")
    camera_b = SimpleNamespace(camera_id="camera-b")
    requested_scope = {}

    class FakeDB:
        def close(self):
            pass

    class FakeCameraRepository:
        def __init__(self, db):
            assert isinstance(db, FakeDB)

        def get_all_cameras(self, owner_id=None, is_admin=False):
            requested_scope.update(owner_id=owner_id, is_admin=is_admin)
            return [camera_a]

    processor = SimpleNamespace(
        _active_alarm_state={"camera-a": True, "camera-b": True},
        _active_alarm_sources={"camera-a": ["fire"], "camera-b": ["security"]},
        _active_tripwire_alarm_states={
            "camera-a": {"wire-a": {"active": True, "event_id": "event-a"}},
            "camera-b": {"wire-b": {"active": True, "event_id": "event-b"}},
        },
    )
    monkeypatch.setattr(websocket_api, "ai_engine", processor)
    monkeypatch.setattr(websocket_api, "SessionLocal", FakeDB)
    monkeypatch.setattr(
        websocket_api,
        "CameraRepository",
        FakeCameraRepository,
    )

    snapshot = websocket_api._build_alarm_state_snapshot("owner-a", "User")

    assert requested_scope == {"owner_id": "owner-a", "is_admin": False}
    assert snapshot == {
        "camera-a": {"active": True, "sources": ["fire"]},
    }

    tripwire_snapshot = websocket_api._build_tripwire_alarm_snapshot(
        "owner-a",
        "User",
    )

    assert tripwire_snapshot == {
        "camera-a": {
            "wire-a": {"active": True, "event_id": "event-a"},
        },
    }
