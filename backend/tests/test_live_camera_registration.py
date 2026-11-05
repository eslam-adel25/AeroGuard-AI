import asyncio
import os
from threading import Event, Thread

import numpy as np
import pytest

from app.api.v1 import cameras
from app.ai.capture import (
    RTSPCaptureError,
    classify_capture_error,
    is_file_source,
    open_capture,
    open_live_capture,
)


def test_validate_live_rtsp_url_accepts_rtsp_and_rtsps():
    assert cameras._validate_live_rtsp_url("rtsp://camera.example/live") == "rtsp://camera.example/live"
    assert cameras._validate_live_rtsp_url("rtsps://camera.example/live") == "rtsps://camera.example/live"


@pytest.mark.parametrize("url", ["", "http://camera.example/live", "rtsp://"])
def test_validate_live_rtsp_url_rejects_invalid_urls(url):
    with pytest.raises(cameras.HTTPException) as error:
        cameras._validate_live_rtsp_url(url)

    assert error.value.status_code == 400


class FakeCapture:
    def __init__(self, opened=True, frame=True):
        self.opened = opened
        self.frame = frame
        self.released = False

    def set(self, *_):
        return True

    def open(self, *_):
        return self.opened

    def isOpened(self):
        return self.opened

    def read(self):
        if not self.frame:
            return False, None
        import numpy as np
        return True, np.zeros((2, 2, 3), dtype=np.uint8)

    def release(self):
        self.released = True


def test_probe_requires_open_stream_and_real_frame(monkeypatch):
    opened_capture = FakeCapture(opened=True, frame=True)
    monkeypatch.setattr(cameras.cv2, "VideoCapture", lambda: opened_capture)
    assert cameras._probe_live_rtsp("rtsp://camera.example/live") is True
    assert opened_capture.released is True

    no_frame_capture = FakeCapture(opened=True, frame=False)
    monkeypatch.setattr(cameras.cv2, "VideoCapture", lambda: no_frame_capture)
    with pytest.raises(RTSPCaptureError) as error:
        cameras._probe_live_rtsp("rtsp://camera.example/live")
    assert error.value.category == "no_frame"
    assert no_frame_capture.released is True


@pytest.mark.parametrize("scheme", ["rtsp", "rtsps"])
def test_rtsp_probe_uses_ffmpeg_timeout_parameters(monkeypatch, scheme):
    capture = FakeCapture()
    calls = []

    def open_with_params(url, backend, params):
        calls.append((url, backend, params))
        return True

    capture.open = open_with_params
    monkeypatch.setattr(cameras.cv2, "VideoCapture", lambda: capture)

    assert cameras._probe_live_rtsp(f"{scheme}://camera.example/live")
    assert capture.released
    assert calls == [
        (
            f"{scheme}://camera.example/live",
            cameras.cv2.CAP_FFMPEG,
            [
                cameras.cv2.CAP_PROP_OPEN_TIMEOUT_MSEC,
                cameras.LIVE_PROBE_TIMEOUT_SECONDS * 1000,
                cameras.cv2.CAP_PROP_READ_TIMEOUT_MSEC,
                cameras.LIVE_PROBE_TIMEOUT_SECONDS * 1000,
            ],
        )
    ]


def test_rtsp_capture_uses_tcp_only_during_explicit_ffmpeg_open(monkeypatch):
    option_name = "OPENCV_FFMPEG_CAPTURE_OPTIONS"
    monkeypatch.setenv(option_name, "some_option;original")
    capture = FakeCapture()
    observed = {}

    def open_with_options(source, backend, params):
        observed["options"] = os.environ.get(option_name)
        observed["backend"] = backend
        observed["params"] = params
        return True

    capture.open = open_with_options

    assert open_live_capture(capture, "rtsp://host/stream")
    assert observed["options"] == "rtsp_transport;tcp"
    assert observed["backend"] == cameras.cv2.CAP_FFMPEG
    assert observed["params"] == [
        cameras.cv2.CAP_PROP_OPEN_TIMEOUT_MSEC,
        cameras.LIVE_PROBE_TIMEOUT_SECONDS * 1000,
        cameras.cv2.CAP_PROP_READ_TIMEOUT_MSEC,
        cameras.LIVE_PROBE_TIMEOUT_SECONDS * 1000,
    ]
    assert os.environ[option_name] == "some_option;original"


@pytest.mark.parametrize(
    ("source", "backend"),
    [
        (0, cameras.cv2.CAP_DSHOW),
        ("D:\\videos\\clip.mp4", None),
    ],
)
def test_non_rtsp_capture_does_not_apply_rtsp_tcp_options(
    monkeypatch,
    source,
    backend,
):
    option_name = "OPENCV_FFMPEG_CAPTURE_OPTIONS"
    monkeypatch.delenv(option_name, raising=False)
    capture = FakeCapture()
    observed = {}

    def open_without_rtsp_options(*args):
        observed["args"] = args
        observed["options"] = os.environ.get(option_name)
        return True

    capture.open = open_without_rtsp_options

    assert open_capture(capture, source, backend=backend)
    assert observed["options"] is None
    if backend is None:
        assert observed["args"] == (source,)
    else:
        assert observed["args"] == (source, backend)


def test_rtsp_options_are_not_visible_during_concurrent_non_rtsp_open(
    monkeypatch,
):
    option_name = "OPENCV_FFMPEG_CAPTURE_OPTIONS"
    monkeypatch.delenv(option_name, raising=False)
    rtsp_open_started = Event()
    release_rtsp_open = Event()
    non_rtsp_open_started = Event()
    observations = {}

    class BlockingCapture:
        def open(self, *args):
            if args[0].startswith("rtsp"):
                observations["rtsp_options"] = os.environ.get(option_name)
                rtsp_open_started.set()
                assert release_rtsp_open.wait(timeout=2)
            else:
                observations["non_rtsp_options"] = os.environ.get(option_name)
                non_rtsp_open_started.set()
            return True

    capture = BlockingCapture()
    rtsp_thread = Thread(
        target=open_live_capture,
        args=(capture, "rtsp://host/stream"),
    )
    file_thread = Thread(
        target=open_capture,
        args=(capture, "D:\\videos\\clip.mp4"),
    )
    rtsp_thread.start()
    assert rtsp_open_started.wait(timeout=2)
    file_thread.start()
    assert not non_rtsp_open_started.wait(timeout=0.05)

    release_rtsp_open.set()
    rtsp_thread.join(timeout=2)
    file_thread.join(timeout=2)

    assert not rtsp_thread.is_alive()
    assert not file_thread.is_alive()
    assert observations == {
        "rtsp_options": "rtsp_transport;tcp",
        "non_rtsp_options": None,
    }


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("rtsp://camera.example/live", False),
        ("rtsps://camera.example/live", False),
        ("https://camera.example/live", False),
        ("rtmp://camera.example/live", False),
        ("D:\\videos\\clip.mp4", True),
        ("relative\\clip.mp4", True),
        ("0", False),
        (0, False),
    ],
)
def test_source_classification_preserves_streams_files_and_local_camera(
    source, expected
):
    assert is_file_source(source) is expected


def test_rtsp_open_fails_safely_when_timeout_parameters_are_unsupported():
    class UnsupportedCapture:
        def open(self, *_):
            raise TypeError("timeout parameters unsupported")

    with pytest.raises(RTSPCaptureError) as error:
        open_live_capture(
            UnsupportedCapture(),
            "rtsp://camera.example/live",
        )

    assert error.value.category == "backend_unavailable"


@pytest.mark.parametrize(
    ("message", "expected_category"),
    [
        ("connection timed out", "connection_timeout"),
        ("Server returned 401 Unauthorized", "authentication_rejected"),
        ("Server returned 403 Forbidden", "authorization_rejected"),
        ("RTSP backend is not available", "backend_unavailable"),
        ("opaque OpenCV error", "open_failed"),
    ],
)
def test_capture_error_classification_uses_only_explicit_evidence(
    message, expected_category
):
    assert classify_capture_error(RuntimeError(message)) == expected_category


def test_rtsp_probe_releases_capture_when_open_fails(monkeypatch):
    capture = FakeCapture(opened=False)
    monkeypatch.setattr(cameras.cv2, "VideoCapture", lambda: capture)

    with pytest.raises(RTSPCaptureError) as error:
        cameras._probe_live_rtsp("rtsp://camera.example/live")

    assert error.value.category == "open_failed"
    assert capture.released


def test_rtsp_probe_releases_capture_when_timeout_parameters_are_unsupported(
    monkeypatch,
):
    class UnsupportedCapture(FakeCapture):
        def open(self, *_):
            raise TypeError("timeout parameters unsupported")

    capture = UnsupportedCapture()
    monkeypatch.setattr(cameras.cv2, "VideoCapture", lambda: capture)

    with pytest.raises(RTSPCaptureError) as error:
        cameras._probe_live_rtsp("rtsp://camera.example/live")

    assert error.value.category == "backend_unavailable"
    assert capture.released


def test_rtsp_probe_releases_capture_when_frame_read_fails(monkeypatch):
    capture = FakeCapture(opened=True, frame=False)
    monkeypatch.setattr(cameras.cv2, "VideoCapture", lambda: capture)

    with pytest.raises(RTSPCaptureError) as error:
        cameras._probe_live_rtsp("rtsp://camera.example/live")

    assert error.value.category == "no_frame"
    assert capture.released


def test_camera_response_redacts_embedded_and_query_credentials():
    stream_url = (
        "rtsp://operator:example@camera.example/live"
        "?username=viewer&password=example&channel=1"
    )

    redacted = cameras._redact_stream_url_credentials(stream_url)

    assert redacted == (
        "rtsp://camera.example/live"
        "?username=REDACTED&password=REDACTED&channel=1"
    )
    assert "operator" not in redacted
    assert "viewer" not in redacted


def test_camera_response_keeps_field_and_redacts_credentials():
    from datetime import datetime, timezone
    from types import SimpleNamespace
    from uuid import uuid4

    camera = SimpleNamespace(
        camera_id=uuid4(),
        camera_name="Test camera",
        location="Test",
        stream_url="rtsp://operator:example@camera.example/live",
        camera_type="LIVE",
        status="Offline",
        created_at=datetime.now(timezone.utc),
    )

    response = cameras._camera_response(camera)

    assert response.stream_url == "rtsp://camera.example/live"
    assert response.camera_type == "LIVE"


def test_mjpeg_encoder_rejects_incomplete_payload(monkeypatch):
    import numpy as np

    monkeypatch.setattr(
        cameras.cv2,
        "imencode",
        lambda *_args, **_kwargs: (
            True,
            np.frombuffer(b"\xff\xd8incomplete", dtype=np.uint8),
        ),
    )

    assert cameras._encode_mjpeg_frame(np.zeros((2, 2, 3), dtype=np.uint8)) is None


def test_mjpeg_encoder_returns_complete_jpeg_payload():
    import numpy as np

    payload = cameras._encode_mjpeg_frame(
        np.zeros((8, 8, 3), dtype=np.uint8)
    )

    assert payload is not None
    assert payload.startswith(b"\xff\xd8")
    assert payload.endswith(b"\xff\xd9")


def test_mjpeg_generator_emits_each_frame_sequence_once(monkeypatch):
    class FakeEngine:
        def __init__(self):
            self.frames = {
                1: np.zeros((2, 2, 3), dtype=np.uint8),
                2: np.ones((2, 2, 3), dtype=np.uint8),
            }

        def get_latest_frame_snapshot(self, _camera_id, after_sequence):
            next_sequence = after_sequence + 1
            if next_sequence not in self.frames:
                return None
            return next_sequence, self.frames[next_sequence]

    monkeypatch.setattr(cameras, "ai_engine", FakeEngine())
    monkeypatch.setattr(
        cameras,
        "_encode_mjpeg_frame",
        lambda frame: b"\xff\xd8" + bytes([int(frame[0, 0, 0])]) + b"\xff\xd9",
    )

    async def read_two_frames():
        generator = cameras.frame_generator("camera-a")
        try:
            return await generator.__anext__(), await generator.__anext__()
        finally:
            await generator.aclose()

    first, second = asyncio.run(read_two_frames())

    assert first.startswith(b"--frame\r\n")
    assert first.endswith(b"\r\n")
    assert second.startswith(b"--frame\r\n")
    assert first != second


def test_mjpeg_generator_uses_sequential_file_playback_frames(monkeypatch):
    class FilePlaybackEngine:
        def __init__(self):
            self.next_sequence = 2

        def get_latest_file_playback_frame(self, _camera_id):
            return 1, b"\xff\xd8frame-1\xff\xd9", 1.0

        def get_next_file_playback_frame(
            self,
            _camera_id,
            after_sequence,
            _timeout,
        ):
            if self.next_sequence > 3 or after_sequence != self.next_sequence - 1:
                return None
            sequence = self.next_sequence
            self.next_sequence += 1
            payload = b"\xff\xd8frame-" + str(sequence).encode() + b"\xff\xd9"
            return sequence, payload, float(sequence)

    monkeypatch.setattr(cameras, "ai_engine", FilePlaybackEngine())

    async def read_three_frames():
        generator = cameras.frame_generator(
            "camera-upload",
            sequential_playback=True,
        )
        try:
            return [await generator.__anext__() for _ in range(3)]
        finally:
            await generator.aclose()

    frames = asyncio.run(read_three_frames())

    assert [frame.split(b"\r\n\r\n", 1)[1].split(b"\r\n", 1)[0] for frame in frames] == [
        b"\xff\xd8frame-1\xff\xd9",
        b"\xff\xd8frame-2\xff\xd9",
        b"\xff\xd8frame-3\xff\xd9",
    ]


def test_uploaded_camera_stream_uses_the_sequential_playback_buffer(monkeypatch):
    from types import SimpleNamespace

    class FilePlaybackEngine:
        def get_latest_file_playback_frame(self, _camera_id):
            return 1, b"\xff\xd8uploaded-frame\xff\xd9", 1.0

    monkeypatch.setattr(cameras, "ai_engine", FilePlaybackEngine())
    monkeypatch.setattr(
        cameras,
        "_get_camera_for_user",
        lambda *_args: SimpleNamespace(camera_type="UPLOAD"),
    )

    async def read_first_frame():
        response = await cameras.get_stream(
            "camera-upload",
            db=None,
            current_user={},
        )
        return await response.body_iterator.__anext__()

    chunk = asyncio.run(read_first_frame())

    assert b"\xff\xd8uploaded-frame\xff\xd9" in chunk


def test_mjpeg_generator_resumes_after_camera_frame_sequence_restarts(monkeypatch):
    class FakeEngine:
        def __init__(self):
            self.sequence = 100

        def get_latest_frame_snapshot(self, _camera_id, after_sequence):
            if self.sequence == after_sequence:
                return None
            return self.sequence, np.zeros((2, 2, 3), dtype=np.uint8)

    engine = FakeEngine()
    monkeypatch.setattr(cameras, "ai_engine", engine)
    monkeypatch.setattr(
        cameras,
        "_encode_mjpeg_frame",
        lambda _frame: b"\xff\xd8\xff\xd9",
    )

    async def read_frames_across_restart():
        generator = cameras.frame_generator("camera-a")
        try:
            first = await generator.__anext__()
            engine.sequence = 1
            restarted = await generator.__anext__()
            return first, restarted
        finally:
            await generator.aclose()

    first, restarted = asyncio.run(read_frames_across_restart())

    assert first.startswith(b"--frame\r\n")
    assert restarted.startswith(b"--frame\r\n")


def test_mjpeg_generator_records_same_diagnostic_sequence_through_jpeg(monkeypatch):
    class Diagnostics:
        def __init__(self):
            self.events = []

        def record_frame(
            self,
            camera_id,
            diagnostic_sequence,
            stage,
            frame,
            capture_timestamp_ns,
        ):
            self.events.append(
                (
                    camera_id,
                    diagnostic_sequence,
                    stage,
                    capture_timestamp_ns,
                    frame.copy(),
                )
            )

        def record_jpeg(
            self,
            camera_id,
            diagnostic_sequence,
            payload,
            capture_timestamp_ns,
        ):
            self.events.append(
                (
                    camera_id,
                    diagnostic_sequence,
                    "G",
                    capture_timestamp_ns,
                    payload,
                )
            )

    class FakeEngine:
        def __init__(self):
            self.frame_diagnostics = Diagnostics()

        def get_next_diagnostic_frame_snapshot(
            self,
            camera_id,
            after_diagnostic_sequence,
        ):
            if after_diagnostic_sequence:
                return None
            return 1, np.full((2, 2, 3), 5, dtype=np.uint8), 27, 987654

        def get_latest_frame_snapshot(self, _camera_id, _after_sequence):
            return None

    engine = FakeEngine()
    monkeypatch.setattr(cameras, "ai_engine", engine)
    expected_payload = b"\xff\xd8jpeg-frame\xff\xd9"
    monkeypatch.setattr(
        cameras,
        "_encode_mjpeg_frame",
        lambda _frame: expected_payload,
    )

    async def read_one_frame():
        generator = cameras.frame_generator("selected-camera")
        try:
            response = await generator.__anext__()
            return response
        finally:
            await generator.aclose()

    response = asyncio.run(read_one_frame())
    events = engine.frame_diagnostics.events

    assert response == (
        b"--frame\r\n"
        b"Content-Type: image/jpeg\r\n\r\n"
        + expected_payload
        + b"\r\n"
    )
    assert [event[2] for event in events] == ["E", "F", "G"]
    assert all(event[0] == "selected-camera" for event in events)
    assert all(event[1] == 27 and event[3] == 987654 for event in events)
    assert events[2][4] == expected_payload


def test_slow_mjpeg_consumer_receives_all_bounded_diagnostic_frames(monkeypatch):
    from app.ai.frame_state import CameraFrameState

    class Diagnostics:
        def __init__(self):
            self.events = []

        def record_frame(
            self,
            camera_id,
            diagnostic_sequence,
            stage,
            frame,
            capture_timestamp_ns,
        ):
            self.events.append(
                (
                    diagnostic_sequence,
                    stage,
                    capture_timestamp_ns,
                    int(frame[0, 0, 0]),
                )
            )

        def record_jpeg(
            self,
            camera_id,
            diagnostic_sequence,
            payload,
            capture_timestamp_ns,
        ):
            self.events.append(
                (
                    diagnostic_sequence,
                    "G",
                    capture_timestamp_ns,
                    payload,
                )
            )

    class FakeEngine:
        def __init__(self):
            self.state = CameraFrameState()
            self.frame_diagnostics = Diagnostics()

        def get_next_diagnostic_frame_snapshot(
            self,
            _camera_id,
            after_diagnostic_sequence,
        ):
            return self.state.get_next_diagnostic_frame(
                after_diagnostic_sequence
            )

        def get_latest_frame_snapshot(self, _camera_id, after_sequence):
            return self.state.get_frame(after_sequence)

    engine = FakeEngine()
    monkeypatch.setattr(cameras, "ai_engine", engine)
    monkeypatch.setattr(
        cameras,
        "_encode_mjpeg_frame",
        lambda frame: b"\xff\xd8" + bytes([int(frame[0, 0, 0])]) + b"\xff\xd9",
    )

    def publish_diagnostic(sequence):
        engine.state.publish(
            np.full((2, 2, 3), sequence, dtype=np.uint8),
            float(sequence),
            diagnostic_sequence=sequence,
            capture_timestamp_ns=10_000 + sequence,
        )

    def publish_normal_frames(start, stop):
        for value in range(start, stop):
            engine.state.publish(
                np.full((2, 2, 3), value, dtype=np.uint8),
                float(value),
            )

    async def consume_slowly():
        generator = cameras.frame_generator("selected-camera")
        try:
            publish_diagnostic(1)
            publish_normal_frames(20, 40)
            first = await generator.__anext__()
            await asyncio.sleep(0.01)

            publish_diagnostic(2)
            publish_diagnostic(3)
            publish_normal_frames(40, 60)
            second = await generator.__anext__()
            await asyncio.sleep(0.01)
            third = await generator.__anext__()
            return first, second, third
        finally:
            await generator.aclose()

    responses = asyncio.run(consume_slowly())
    encoded_values = [
        response.split(b"\r\n\r\n", 1)[1][:-2][2]
        for response in responses
    ]
    events = engine.frame_diagnostics.events
    jpeg_events = [event for event in events if event[1] == "G"]

    assert encoded_values == [1, 2, 3]
    assert [event[0] for event in jpeg_events] == [1, 2, 3]
    assert [event[2] for event in jpeg_events] == [10001, 10002, 10003]
    assert [event[3][2] for event in jpeg_events] == [1, 2, 3]
    assert len(engine.state._diagnostic_frames) == 3


def test_verify_live_rtsp_reports_probe_failure(monkeypatch):
    def fail_probe(_):
        raise RTSPCaptureError("no_frame")

    monkeypatch.setattr(
        cameras,
        "_probe_live_rtsp",
        fail_probe,
    )

    with pytest.raises(cameras.HTTPException) as error:
        asyncio.run(cameras._verify_live_rtsp("rtsp://camera.example/live"))

    assert error.value.status_code == 400
    assert error.value.detail == "RTSP stream opened but no frame was received"
