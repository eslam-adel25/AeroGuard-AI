import hashlib
import json

import cv2
import numpy as np

from app.ai.frame_diagnostics import FrameDiagnostics, MAX_DIAGNOSTIC_FRAMES


def test_diagnostics_are_disabled_without_explicit_opt_in(monkeypatch, tmp_path):
    monkeypatch.delenv("AEROGUARD_FRAME_DIAGNOSTICS", raising=False)
    monkeypatch.setenv(
        "AEROGUARD_FRAME_DIAGNOSTICS_DIR",
        str(tmp_path / "must-not-be-created"),
    )

    assert FrameDiagnostics.from_environment() is None
    assert not (tmp_path / "must-not-be-created").exists()


def test_diagnostics_require_explicit_camera_and_absolute_output_directory(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setenv("AEROGUARD_FRAME_DIAGNOSTICS", "1")
    monkeypatch.setenv("AEROGUARD_FRAME_DIAGNOSTICS_CAMERA_ID", "camera-opt-in")
    monkeypatch.setenv(
        "AEROGUARD_FRAME_DIAGNOSTICS_DIR",
        str(tmp_path / "diagnostics"),
    )
    diagnostics = FrameDiagnostics.from_environment()
    assert diagnostics is not None
    diagnostics.close()
    assert diagnostics.output_dir.parent == (tmp_path / "diagnostics").resolve()

    monkeypatch.setenv("AEROGUARD_FRAME_DIAGNOSTICS_DIR", "relative-output")
    try:
        FrameDiagnostics.from_environment()
    except ValueError as error:
        assert "absolute" in str(error)
    else:
        raise AssertionError("relative output directory should be rejected")


def test_diagnostics_capture_bounded_frames_for_only_selected_camera(tmp_path):
    camera_id = "selected-camera-123"
    diagnostics = FrameDiagnostics(camera_id, tmp_path)
    capture_timestamp_ns = 987654321
    frame = np.full((8, 12, 3), 73, dtype=np.uint8)

    assert diagnostics.begin_frame(
        "another-camera",
        frame,
        capture_timestamp_ns,
    ) is None
    first_sequence = diagnostics.begin_frame(
        camera_id,
        frame,
        capture_timestamp_ns,
    )
    frame[:] = 0
    assert first_sequence == 1

    for sequence in range(2, MAX_DIAGNOSTIC_FRAMES + 1):
        assert diagnostics.begin_frame(
            camera_id,
            np.full((8, 12, 3), sequence, dtype=np.uint8),
            capture_timestamp_ns + sequence,
        ) == sequence
    assert diagnostics.begin_frame(
        camera_id,
        frame,
        capture_timestamp_ns,
    ) is None
    diagnostics.close()

    records = [
        json.loads(line)
        for line in (diagnostics.output_dir / "frames.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert len(records) == MAX_DIAGNOSTIC_FRAMES
    assert [record["sequence"] for record in records] == [1, 2, 3]
    assert all(record["stage"] == "A" for record in records)
    assert all(
        record["capture_timestamp_monotonic_ns"] == capture_timestamp_ns
        or record["sequence"] in (2, 3)
        for record in records
    )
    assert all(record["width"] == 12 and record["height"] == 8 for record in records)
    assert all(record["dtype"] == "uint8" for record in records)
    assert all(record["channels"] == 3 for record in records)
    assert all(record["jpeg_encode_success"] for record in records)
    assert all(record["jpeg_decode_success"] for record in records)
    assert all(
        record["camera_hash"]
        == hashlib.sha256(camera_id.encode("utf-8")).hexdigest()[:16]
        for record in records
    )
    assert camera_id not in (diagnostics.output_dir / "frames.jsonl").read_text(
        encoding="utf-8"
    )

    saved = cv2.imread(
        str(diagnostics.output_dir / records[0]["file"]),
        cv2.IMREAD_COLOR,
    )
    assert saved is not None
    assert np.all(saved > 0)


def test_diagnostics_save_the_exact_mjpeg_jpeg_and_validate_decoding(tmp_path):
    diagnostics = FrameDiagnostics("camera-x", tmp_path)
    frame = np.full((10, 14, 3), 111, dtype=np.uint8)
    encoded, buffer = cv2.imencode(".jpg", frame)
    assert encoded
    payload = buffer.tobytes()

    sequence = diagnostics.begin_frame("camera-x", frame, 456)
    diagnostics.record_jpeg("camera-x", sequence, payload, 456)
    diagnostics.close()

    records = [
        json.loads(line)
        for line in (diagnostics.output_dir / "frames.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    jpeg_record = next(record for record in records if record["stage"] == "G")
    saved_payload = (diagnostics.output_dir / jpeg_record["file"]).read_bytes()

    assert jpeg_record["sequence"] == sequence
    assert jpeg_record["capture_timestamp_monotonic_ns"] == 456
    assert jpeg_record["width"] == 14
    assert jpeg_record["height"] == 10
    assert jpeg_record["channels"] == 3
    assert jpeg_record["jpeg_encode_success"]
    assert jpeg_record["jpeg_decode_success"]
    assert saved_payload == payload


def test_diagnostics_ignore_frames_from_other_cameras(tmp_path):
    diagnostics = FrameDiagnostics("selected-camera", tmp_path)
    frame = np.zeros((2, 2, 3), dtype=np.uint8)

    assert diagnostics.begin_frame("unselected-camera", frame, 1) is None
    diagnostics.close()
    assert not (diagnostics.output_dir / "frames.jsonl").exists()
    assert not diagnostics._worker.is_alive()


def test_diagnostics_record_pipeline_timings_only_for_selected_camera(tmp_path):
    diagnostics = FrameDiagnostics("selected-camera", tmp_path)
    timings = {
        "capture_timestamp_monotonic_ns": 10,
        "inference_start_monotonic_ns": 20,
        "model_lock_wait_ms": 1.5,
    }

    diagnostics.record_timing("other-camera", 1, timings)
    diagnostics.record_timing("selected-camera", 12, timings)
    diagnostics.close()

    records = [
        json.loads(line)
        for line in (diagnostics.output_dir / "frames.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert len(records) == 1
    assert records[0]["sequence"] == 12
    assert records[0]["stage"] == "timing"
    assert records[0]["timings"] == timings
    assert "selected-camera" not in json.dumps(records[0])
    assert diagnostics._queued_stages == set()


def test_ai_processor_close_releases_diagnostics_once(monkeypatch):
    from app.ai.processor import AIProcessor

    class Diagnostics:
        def __init__(self):
            self.close_calls = 0

        def close(self):
            self.close_calls += 1

    diagnostics = Diagnostics()
    processor = AIProcessor.__new__(AIProcessor)
    processor.frame_diagnostics = diagnostics

    processor.close()
    processor.close()

    assert processor.frame_diagnostics is None
    assert diagnostics.close_calls == 1


def test_application_shutdown_closes_ai_processor(monkeypatch):
    from app import main

    class Engine:
        def __init__(self):
            self.close_calls = 0

        def close(self):
            self.close_calls += 1

    engine = Engine()
    monkeypatch.setattr(main, "ai_engine", engine)
    app = main.create_app()
    shutdown = next(
        callback
        for callback in app.router.on_shutdown
        if callback.__name__ == "shutdown_event"
    )

    shutdown()

    assert engine.close_calls == 1
