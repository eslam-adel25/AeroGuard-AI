import time
from collections import deque
from threading import Condition, Lock


class RollingFrameRate:
    def __init__(self, window_seconds: float = 2.0, minimum_span_seconds: float = 1.0):
        self.window_seconds = window_seconds
        self.minimum_span_seconds = minimum_span_seconds
        self._timestamps = deque(maxlen=512)

    def record(self, timestamp: float) -> None:
        if self._timestamps and timestamp <= self._timestamps[-1]:
            return
        self._timestamps.append(timestamp)
        cutoff = timestamp - self.window_seconds
        while self._timestamps and self._timestamps[0] < cutoff:
            self._timestamps.popleft()

    def value(self, now: float) -> float:
        cutoff = now - self.window_seconds
        while self._timestamps and self._timestamps[0] < cutoff:
            self._timestamps.popleft()
        if len(self._timestamps) < 2:
            return 0.0
        elapsed = self._timestamps[-1] - self._timestamps[0]
        if elapsed < self.minimum_span_seconds:
            return 0.0
        return round((len(self._timestamps) - 1) / elapsed, 1)


class CameraFrameState:
    def __init__(self):
        self._lock = Lock()
        self._capture_rate = RollingFrameRate()
        self._processing_rate = RollingFrameRate()
        self._output_rate = RollingFrameRate()
        self._frame = None
        self._sequence = 0
        self._diagnostic_sequence = None
        self._capture_timestamp_ns = None
        self._diagnostic_frames = deque(maxlen=3)

    def record_capture(self, timestamp: float) -> None:
        with self._lock:
            self._capture_rate.record(timestamp)

    def record_processing(self, timestamp: float) -> None:
        with self._lock:
            self._processing_rate.record(timestamp)

    def publish(
        self,
        frame,
        timestamp: float,
        diagnostic_sequence: int | None = None,
        capture_timestamp_ns: int | None = None,
    ):
        snapshot = frame.copy()
        with self._lock:
            self._frame = snapshot
            self._sequence += 1
            self._diagnostic_sequence = diagnostic_sequence
            self._capture_timestamp_ns = capture_timestamp_ns
            self._output_rate.record(timestamp)
            if diagnostic_sequence is not None:
                self._diagnostic_frames.append(
                    (
                        self._sequence,
                        snapshot,
                        diagnostic_sequence,
                        capture_timestamp_ns,
                    )
                )
            return snapshot

    def get_frame(self, after_sequence: int = 0):
        with self._lock:
            if self._frame is None or self._sequence == after_sequence:
                return None
            return self._sequence, self._frame.copy()

    def get_frame_with_metadata(self, after_sequence: int = 0):
        with self._lock:
            if self._frame is None or self._sequence == after_sequence:
                return None
            return (
                self._sequence,
                self._frame.copy(),
                self._diagnostic_sequence,
                self._capture_timestamp_ns,
            )

    def get_next_diagnostic_frame(self, after_diagnostic_sequence: int = 0):
        with self._lock:
            for sequence, frame, diagnostic_sequence, capture_timestamp_ns in (
                self._diagnostic_frames
            ):
                if diagnostic_sequence > after_diagnostic_sequence:
                    return (
                        sequence,
                        frame.copy(),
                        diagnostic_sequence,
                        capture_timestamp_ns,
                    )
            return None

    def metrics(self, now: float) -> dict[str, float]:
        with self._lock:
            return {
                "capture_fps": self._capture_rate.value(now),
                "processing_fps": self._processing_rate.value(now),
                "output_fps": self._output_rate.value(now),
            }


class CameraPipelineState:
    """Per-camera dual live/AI pipeline state backed by independent readers."""

    def __init__(self):
        self.live_reader = CameraFrameState()
        self.file_playback_buffer = SequentialFrameBuffer(maxlen=64)
        self.ai_capture_buffer = LatestFrameBuffer(maxlen=1)
        self.ai_buffer = LatestFrameBuffer(maxlen=1)

    def publish_live_frame(self, frame, timestamp=None):
        return self.live_reader.publish(frame, time.monotonic() if timestamp is None else timestamp)

    def get_live_frame(self, after_sequence=0):
        return self.live_reader.get_frame(after_sequence)

    def publish_file_playback_frame(self, payload, timestamp=None):
        return self.file_playback_buffer.publish(payload, timestamp)

    def get_latest_file_playback_frame(self):
        return self.file_playback_buffer.get_latest()

    def get_next_file_playback_frame(self, after_sequence=0, timeout=None):
        return self.file_playback_buffer.get_next(after_sequence, timeout)

    def publish_ai_capture_frame(self, frame, timestamp=None, metadata=None):
        return self.ai_capture_buffer.publish(frame, timestamp, metadata)

    def get_ai_capture_frame(self, after_sequence=0, timeout=None):
        return self.ai_capture_buffer.wait_for_latest(after_sequence, timeout)

    def publish_ai_frame(self, frame, timestamp=None, metadata=None):
        return self.ai_buffer.publish(frame, timestamp, metadata)

    def get_ai_frame(self, after_sequence=0):
        return self.ai_buffer.get_latest(after_sequence)

    def clear(self):
        self.live_reader = CameraFrameState()
        self.file_playback_buffer.clear()
        self.ai_capture_buffer.clear()
        self.ai_buffer.clear()


class SequentialFrameBuffer:
    """Bounded FIFO for playback frames; separate from latest-only AI buffers."""

    def __init__(self, maxlen: int = 64):
        self._condition = Condition()
        self._frames = deque(maxlen=max(1, int(maxlen)))
        self._sequence = 0

    def publish(self, payload: bytes, timestamp: float | None = None):
        if not payload:
            return None
        with self._condition:
            self._sequence += 1
            self._frames.append(
                {
                    "payload": bytes(payload),
                    "timestamp": timestamp,
                    "sequence": self._sequence,
                }
            )
            self._condition.notify_all()
            return self._sequence

    def get_latest(self):
        with self._condition:
            if not self._frames:
                return None
            latest = self._frames[-1]
            return latest["sequence"], latest["payload"], latest["timestamp"]

    def get_next(self, after_sequence: int = 0, timeout=None):
        with self._condition:
            self._condition.wait_for(
                lambda: bool(self._frames)
                and (
                    self._frames[-1]["sequence"] > after_sequence
                    or self._frames[-1]["sequence"] < after_sequence
                ),
                timeout=timeout,
            )
            if not self._frames:
                return None
            oldest = self._frames[0]
            if oldest["sequence"] > after_sequence + 1:
                return oldest["sequence"], oldest["payload"], oldest["timestamp"]
            if self._frames[-1]["sequence"] < after_sequence:
                latest = self._frames[-1]
                return latest["sequence"], latest["payload"], latest["timestamp"]
            for frame in self._frames:
                if frame["sequence"] > after_sequence:
                    return frame["sequence"], frame["payload"], frame["timestamp"]
            return None

    def clear(self):
        with self._condition:
            self._frames.clear()
            self._sequence = 0
            self._condition.notify_all()


class LatestFrameBuffer:
    """Bounded latest-frame store used for AI scheduling and live previews."""

    def __init__(self, maxlen: int = 1):
        self._condition = Condition()
        self._maxlen = max(1, int(maxlen))
        self._frames = deque(maxlen=self._maxlen)
        self._sequence = 0

    def publish(self, frame, timestamp: float | None = None, metadata=None):
        if frame is None:
            return None
        snapshot = frame.copy()
        with self._condition:
            self._sequence += 1
            self._frames.clear()
            self._frames.append(
                {
                    "frame": snapshot,
                    "timestamp": timestamp,
                    "metadata": dict(metadata) if metadata is not None else None,
                    "sequence": self._sequence,
                }
            )
            self._condition.notify_all()
            return self._sequence, snapshot

    def get_latest(self, after_sequence: int = 0):
        snapshot = self.get_latest_snapshot(after_sequence)
        if snapshot is None:
            return None
        return snapshot[0], snapshot[1]

    def get_latest_snapshot(self, after_sequence: int = 0):
        with self._condition:
            if not self._frames:
                return None
            latest = self._frames[-1]
            if latest["sequence"] <= after_sequence:
                return None
            return (
                latest["sequence"],
                latest["frame"].copy(),
                latest["timestamp"],
                dict(latest["metadata"])
                if latest["metadata"] is not None
                else None,
            )

    def wait_for_latest(self, after_sequence: int = 0, timeout=None):
        with self._condition:
            self._condition.wait_for(
                lambda: bool(self._frames)
                and self._frames[-1]["sequence"] > after_sequence,
                timeout=timeout,
            )
            if not self._frames:
                return None
            latest = self._frames[-1]
            if latest["sequence"] <= after_sequence:
                return None
            return (
                latest["sequence"],
                latest["frame"].copy(),
                latest["timestamp"],
                dict(latest["metadata"])
                if latest["metadata"] is not None
                else None,
            )

    def clear(self):
        with self._condition:
            self._frames.clear()
            self._sequence = 0
            self._condition.notify_all()
