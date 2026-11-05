import threading
import time

import cv2
import numpy as np
import pytest

from app.ai.capture import CameraSourceError, resolve_camera_source
from app.ai.capture_reader import CameraCaptureReader
from app.ai.frame_state import LatestFrameBuffer
from app.ai.processor import AIProcessor


def test_latest_frame_buffer_keeps_only_latest_frame():
    buffer = LatestFrameBuffer(maxlen=1)
    first = np.zeros((8, 8, 3), dtype=np.uint8)
    second = np.full((8, 8, 3), 255, dtype=np.uint8)

    buffer.publish(first)
    buffer.publish(second)

    sequence, frame = buffer.get_latest()
    assert sequence == 2
    assert np.array_equal(frame, second)


def test_camera_source_resolver_routes_rtsp_usb_and_uploaded_files():
    assert resolve_camera_source(
        "NVR",
        "rtsp://recorder.example/live",
    ) == ("rtsp", "rtsp://recorder.example/live")
    assert resolve_camera_source("USB", "0") == ("device", 0)
    assert resolve_camera_source("UPLOAD", "archive.mp4") == (
        "file",
        "archive.mp4",
    )
    with pytest.raises(CameraSourceError):
        resolve_camera_source("NVR", "https://recorder.example/live")


def test_uploaded_playback_callback_runs_on_the_source_read_thread():
    class FiniteFileCapture:
        def __init__(self):
            self.read_count = 0
            self.opened = True

        def read(self):
            self.read_count += 1
            if self.read_count > 3:
                return False, None
            return True, np.full((4, 4, 3), self.read_count, dtype=np.uint8)

        def get(self, _property):
            return 3

        def isOpened(self):
            return self.opened

        def release(self):
            self.opened = False

    callback_threads = []
    reader = CameraCaptureReader(
        "uploaded-camera",
        FiniteFileCapture(),
        LatestFrameBuffer(),
        lambda *_args: None,
        lambda: False,
        1.0,
        file_source=True,
        on_file_frame=lambda *_args: callback_threads.append(
            threading.get_ident()
        ),
    )
    reader.start()
    reader.join(timeout=2)
    reader._capture_thread.join(timeout=2)

    assert len(callback_threads) == 3
    assert set(callback_threads) == {reader._capture_thread.ident}


def test_file_reader_does_not_accumulate_scheduler_oversleep(monkeypatch):
    class FakeClock:
        current = 0.0

        def monotonic(self):
            return self.current

    class FiniteFileCapture:
        frame_count = 6

        def __init__(self):
            self.read_count = 0

        def read(self):
            self.read_count += 1
            if self.read_count > self.frame_count:
                return False, None
            return True, np.full((2, 2, 3), self.read_count, dtype=np.uint8)

        def get(self, property_id):
            if property_id == cv2.CAP_PROP_FRAME_COUNT:
                return self.frame_count
            if property_id == cv2.CAP_PROP_POS_FRAMES:
                return min(self.read_count, self.frame_count)
            return 0

        def release(self):
            pass

    clock = FakeClock()
    monkeypatch.setattr("app.ai.capture_reader.time.monotonic", clock.monotonic)
    timestamps = []
    reader = CameraCaptureReader(
        "uploaded-camera",
        FiniteFileCapture(),
        LatestFrameBuffer(),
        lambda *_args: None,
        lambda: False,
        1.0,
        file_source=True,
        frame_period=0.1,
        on_file_frame=lambda _frame, timestamp: timestamps.append(timestamp),
    )

    def wait_with_oversleep(timeout):
        clock.current += max(0.0, timeout) + 0.02
        return False

    monkeypatch.setattr(reader._stop_event, "wait", wait_with_oversleep)
    reader.start()
    reader.join(timeout=2)
    reader._capture_thread.join(timeout=2)

    assert len(timestamps) == 6
    assert timestamps[-1] - timestamps[0] == pytest.approx(0.52)


def test_live_and_ai_buffers_are_isolated_per_camera():
    processor = AIProcessor.__new__(AIProcessor)
    processor.live_frame_states = {}
    processor.live_frame_lock = threading.Lock()
    processor.ai_frame_buffers = {}
    processor.ai_frame_lock = threading.Lock()

    raw_frame = np.zeros((12, 12, 3), dtype=np.uint8)
    ai_frame = np.full((12, 12, 3), 128, dtype=np.uint8)

    processor.publish_live_frame("camera-a", raw_frame)
    processor._get_ai_frame_buffer("camera-a").publish(ai_frame)

    live_snapshot = processor.get_live_frame_snapshot("camera-a")
    ai_snapshot = processor.get_ai_frame_snapshot("camera-a")

    assert live_snapshot is not None
    assert ai_snapshot is not None
    assert np.array_equal(live_snapshot[1], raw_frame)
    assert np.array_equal(ai_snapshot[1], ai_frame)


def test_capture_readers_continue_during_blocked_inference_and_are_isolated():
    processor = AIProcessor.__new__(AIProcessor)
    processor.camera_pipelines = {}
    processor.live_frame_lock = threading.Lock()
    processor.live_frame_states = {}
    processor.ai_frame_buffers = {}
    processor.ai_frame_lock = threading.Lock()
    processor._frame_states = {}
    processor._frame_states_lock = threading.Lock()
    processor._active_camera_lock = threading.Lock()
    processor._model_lock = threading.Lock()
    processor._active_cameras = set()
    processor._starting_cameras = set()
    processor._camera_started_at = {}
    processor._last_frame_received_at = {}
    processor._stop_flags = {}
    processor._source_readers = {}
    processor._source_readers_lock = threading.Lock()
    processor._source_started_at = {}
    processor._source_last_frame_received_at = {}
    processor._source_stop_flags = set()
    processor.last_frames = {}

    class FastCapture:
        def __init__(self, value):
            self.value = value
            self.sequence = 0
            self.opened = True

        def read(self):
            time.sleep(0.002)
            self.sequence += 1
            return True, np.full(
                (4, 4, 3),
                (self.value + self.sequence) % 255,
                dtype=np.uint8,
            )

        def release(self):
            self.opened = False

        def isOpened(self):
            return self.opened

    def create_reader(camera_id, capture):
        return CameraCaptureReader(
            camera_id,
            capture,
            processor._get_ai_capture_buffer(camera_id),
            lambda frame, timestamp: processor._publish_capture_frame(
                camera_id,
                frame,
                timestamp,
            ),
            lambda: processor._source_stop_requested(camera_id),
            1.0,
        )

    reader_a = create_reader("camera-a", FastCapture(10))
    reader_b = create_reader("camera-b", FastCapture(100))
    processor.reserve_camera_start("camera-a")
    processor.reserve_camera_start("camera-b")
    processor.register_camera_source_reader("camera-a", reader_a)
    processor.register_camera_source_reader("camera-b", reader_b)
    inference_started = threading.Event()
    unblock_inference = threading.Event()
    processed_sequences = []

    class BlockingModel:
        names = {}

        def predict(self, *_args, **_kwargs):
            inference_started.set()
            unblock_inference.wait(timeout=2)
            return []

    processor.model = BlockingModel()

    def blocked_inference():
        frame = processor.get_ai_capture_frame_snapshot(
            "camera-a",
            timeout=1,
        )
        assert frame is not None
        processed_sequences.append(frame[0])
        processor._predict_frame(frame[1], 0.5)

    inference_thread = threading.Thread(target=blocked_inference)
    inference_thread.start()
    try:
        assert inference_started.wait(timeout=1)
        first_a = reader_a.wait_for_frame(0, timeout=1)
        first_b = reader_b.wait_for_frame(0, timeout=1)
        assert first_a is not None
        assert first_b is not None

        time.sleep(0.1)
        latest_a = reader_a.wait_for_frame(first_a[0], timeout=1)
        latest_b = reader_b.wait_for_frame(first_b[0], timeout=1)
        assert latest_a is not None
        assert latest_b is not None
        assert latest_a[0] > first_a[0]
        assert latest_b[0] > first_b[0]
        assert processor.get_live_frame_snapshot("camera-a")[0] > 1
        assert processor.get_live_frame_snapshot("camera-b")[0] > 1
        assert len(processor._get_ai_capture_buffer("camera-a")._frames) == 1
        assert len(processor._get_ai_capture_buffer("camera-b")._frames) == 1

        processor.stop_camera("camera-a")
        before_stopped_ai_a = processor.get_ai_capture_frame_snapshot("camera-a")[0]
        before_b = processor.get_ai_capture_frame_snapshot("camera-b")[0]
        time.sleep(0.05)
        after_stopped_ai_a = processor.get_ai_capture_frame_snapshot("camera-a")[0]
        after_b = processor.get_ai_capture_frame_snapshot("camera-b")[0]
        assert after_stopped_ai_a > before_stopped_ai_a
        assert after_b > before_b
        assert processor.get_camera_runtime_statuses(["camera-a"])[
            "camera-a"
        ]["source_active"]

        unblock_inference.set()
        inference_thread.join(timeout=1)
        processor.release_camera_start("camera-a")
        assert not processor.get_camera_runtime_statuses(["camera-a"])[
            "camera-a"
        ]["ai_processing"]
        before_b = processor.get_ai_capture_frame_snapshot("camera-b")[0]
        processor.stop_camera_source("camera-a")
        time.sleep(0.05)
        assert processor.get_ai_capture_frame_snapshot("camera-b")[0] > before_b
        assert not processor.has_active_camera_source("camera-a")
        assert processor.has_active_camera_source("camera-b")
    finally:
        unblock_inference.set()
        processor.stop_camera_source("camera-a")
        processor.stop_camera_source("camera-b")
        inference_thread.join(timeout=1)
    assert processed_sequences[0] < latest_a[0]
