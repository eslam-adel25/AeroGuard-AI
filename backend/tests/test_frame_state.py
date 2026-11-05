import numpy as np

from app.ai.frame_state import (
    CameraFrameState,
    CameraPipelineState,
    RollingFrameRate,
    SequentialFrameBuffer,
)


def test_rolling_frame_rate_uses_elapsed_window_not_single_frame_latency():
    rate = RollingFrameRate()

    rate.record(1.0)
    rate.record(1.005)
    assert rate.value(1.005) == 0.0

    rate = RollingFrameRate()
    for index in range(1, 61):
        rate.record(1.0 + index / 30)

    assert rate.value(3.0) == 30.0


def test_rolling_frame_rate_ignores_duplicate_and_non_monotonic_samples():
    rate = RollingFrameRate()

    for timestamp in (1.0, 1.0, 0.9, 2.0, 3.0):
        rate.record(timestamp)

    assert rate.value(3.0) == 1.0


def test_frame_metrics_count_capture_processing_and_output_separately():
    state = CameraFrameState()
    for timestamp in range(1, 33):
        state.record_capture(timestamp / 30)
        state.publish(np.zeros((2, 2, 3), dtype=np.uint8), timestamp / 30)
        if timestamp % 2 == 0:
            state.record_processing(timestamp / 30)

    metrics = state.metrics(2.0)

    assert metrics == {
        "capture_fps": 30.0,
        "processing_fps": 15.0,
        "output_fps": 30.0,
    }


def test_frame_state_keeps_only_latest_sequence_and_returns_isolated_copies():
    state = CameraFrameState()
    old_frame = np.zeros((2, 2, 3), dtype=np.uint8)
    new_frame = np.full((2, 2, 3), 255, dtype=np.uint8)

    state.publish(old_frame, 1.0)
    state.publish(new_frame, 2.0)

    assert state.get_frame(after_sequence=0)[0] == 2
    assert state.get_frame(after_sequence=1)[0] == 2
    assert state.get_frame(after_sequence=2) is None

    sequence, frame = state.get_frame(after_sequence=0)
    frame[:] = 0
    assert sequence == 2
    assert state.get_frame(after_sequence=0)[1].min() == 255


def test_frame_state_exposes_restarted_sequence_to_existing_stream_consumer():
    restarted_state = CameraFrameState()
    restarted_state.publish(
        np.full((2, 2, 3), 255, dtype=np.uint8),
        1.0,
    )

    snapshot = restarted_state.get_frame(after_sequence=100)

    assert snapshot is not None
    assert snapshot[0] == 1


def test_frame_state_propagates_diagnostic_sequence_and_capture_timestamp():
    state = CameraFrameState()
    frame = np.full((2, 3, 3), 127, dtype=np.uint8)

    state.publish(
        frame,
        1.0,
        diagnostic_sequence=19,
        capture_timestamp_ns=123456789,
    )
    snapshot = state.get_frame_with_metadata()

    assert snapshot is not None
    sequence, stored_frame, diagnostic_sequence, capture_timestamp_ns = snapshot
    assert sequence == 1
    assert diagnostic_sequence == 19
    assert capture_timestamp_ns == 123456789
    assert np.array_equal(stored_frame, frame)
    stored_frame[:] = 0
    assert np.array_equal(state.get_frame_with_metadata()[1], frame)


def test_diagnostic_frame_snapshots_survive_faster_normal_frame_publication():
    state = CameraFrameState()
    diagnostic_frames = []
    for diagnostic_sequence in range(1, 4):
        frame = np.full(
            (2, 2, 3),
            diagnostic_sequence,
            dtype=np.uint8,
        )
        state.publish(
            frame,
            float(diagnostic_sequence),
            diagnostic_sequence=diagnostic_sequence,
            capture_timestamp_ns=1000 + diagnostic_sequence,
        )
        diagnostic_frames.append(frame.copy())

    for value in range(20, 40):
        state.publish(
            np.full((2, 2, 3), value, dtype=np.uint8),
            float(value),
        )

    snapshots = [
        state.get_next_diagnostic_frame(after_sequence)
        for after_sequence in (0, 1, 2)
    ]

    assert [snapshot[2] for snapshot in snapshots] == [1, 2, 3]
    assert [snapshot[3] for snapshot in snapshots] == [1001, 1002, 1003]
    for snapshot, original in zip(snapshots, diagnostic_frames):
        assert np.array_equal(snapshot[1], original)
    assert state.get_next_diagnostic_frame(3) is None
    assert state.get_frame()[1][0, 0, 0] == 39


def test_sequential_playback_buffer_preserves_frames_after_consumer_delay():
    playback = SequentialFrameBuffer(maxlen=4)
    for sequence in range(1, 5):
        playback.publish(f"frame-{sequence}".encode(), float(sequence))

    frames = [playback.get_next(after_sequence) for after_sequence in range(4)]

    assert [frame[0] for frame in frames] == [1, 2, 3, 4]
    assert [frame[1] for frame in frames] == [
        b"frame-1",
        b"frame-2",
        b"frame-3",
        b"frame-4",
    ]


def test_sequential_playback_buffer_is_bounded_and_recovers_after_restart():
    playback = SequentialFrameBuffer(maxlen=2)
    for sequence in range(1, 4):
        playback.publish(f"frame-{sequence}".encode())

    assert playback.get_next(0)[0] == 2
    playback.clear()
    playback.publish(b"restarted-frame")

    restarted = playback.get_next(after_sequence=3)
    assert restarted[0] == 1
    assert restarted[1] == b"restarted-frame"


def test_file_playback_sequence_is_independent_of_latest_only_ai_buffer():
    pipeline = CameraPipelineState()
    frame = np.ones((2, 2, 3), dtype=np.uint8)
    pipeline.publish_live_frame(frame, 1.0)
    pipeline.publish_file_playback_frame(b"jpeg-1", 1.0)
    pipeline.publish_file_playback_frame(b"jpeg-2", 2.0)
    pipeline.publish_ai_capture_frame(frame, 2.0)
    pipeline.publish_ai_frame(frame, 2.0)

    assert pipeline.get_live_frame()[0] == 1
    assert pipeline.get_latest_file_playback_frame()[0] == 2
    assert pipeline.get_next_file_playback_frame(0)[1] == b"jpeg-1"
    assert pipeline.get_ai_capture_frame()[0] == 1
    assert pipeline.get_ai_frame()[0] == 1
