import logging
import queue
import threading
import time
from collections.abc import Callable

import cv2


logger = logging.getLogger(__name__)
MAX_RECONNECT_ATTEMPTS = 3


class CameraCaptureReader:
    def __init__(
        self,
        camera_id: str,
        capture,
        frame_buffer,
        on_frame: Callable,
        stop_requested: Callable[[], bool],
        no_frame_grace_seconds: float,
        file_source: bool = False,
        frame_period: float | None = None,
        reopen_capture: Callable[[], object] | None = None,
        on_file_frame: Callable | None = None,
    ):
        self.camera_id = str(camera_id)
        self.capture = capture
        self.frame_buffer = frame_buffer
        self.on_frame = on_frame
        self.stop_requested = stop_requested
        self.no_frame_grace_seconds = no_frame_grace_seconds
        self.file_source = file_source
        self.frame_period = frame_period
        self.reopen_capture = reopen_capture
        self.on_file_frame = on_file_frame
        self._stop_event = threading.Event()
        self._done_event = threading.Event()
        self._release_lock = threading.Lock()
        self._released_capture_ids = set()
        self._read_results = queue.Queue(maxsize=1)
        self._capture_thread = None
        self._thread = threading.Thread(
            target=self._run,
            name=f"aeroguard-capture-{self.camera_id}",
            daemon=True,
        )
        self.error = None

    @property
    def done(self):
        return self._done_event.is_set()

    def start(self):
        self._start_capture_thread()
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self.capture is not None:
            self._release_capture(self.capture)

    def _release_capture(self, capture):
        capture_id = id(capture)
        with self._release_lock:
            if capture_id in self._released_capture_ids:
                return
            self._released_capture_ids.add(capture_id)
        try:
            capture.release()
        except Exception as exc:
            logger.warning(
                "Camera capture release failed camera_id=%s error=%s",
                self.camera_id,
                type(exc).__name__,
            )

    def join(self, timeout=None):
        self._thread.join(timeout)

    def is_alive(self):
        return self._thread.is_alive()

    def wait_for_frame(self, after_sequence: int, timeout=None):
        return self.frame_buffer.wait_for_latest(after_sequence, timeout)

    def _publish_read_result(self, capture, result):
        if capture is not self.capture:
            return
        item = (capture, result)
        try:
            self._read_results.put_nowait(item)
            return
        except queue.Full:
            pass
        try:
            self._read_results.get_nowait()
        except queue.Empty:
            pass
        try:
            self._read_results.put_nowait(item)
        except queue.Full:
            pass

    def _start_capture_thread(self):
        capture = self.capture

        def read_frames():
            next_frame_at = time.monotonic()
            while (
                not self._stop_event.is_set()
                and not self.stop_requested()
                and capture is self.capture
            ):
                try:
                    result = capture.read()
                except Exception as exc:
                    self._publish_read_result(capture, exc)
                    return
                if (
                    self.file_source
                    and self.on_file_frame is not None
                    and not isinstance(result, Exception)
                    and result[0]
                    and result[1] is not None
                ):
                    try:
                        self.on_file_frame(result[1], time.monotonic())
                    except Exception as exc:
                        self._publish_read_result(capture, exc)
                        return
                self._publish_read_result(capture, result)
                if (
                    self.file_source
                    and self.frame_period
                    and not isinstance(result, Exception)
                    and result[0]
                    and result[1] is not None
                ):
                    next_frame_at += self.frame_period
                    self._stop_event.wait(
                        max(0.0, next_frame_at - time.monotonic())
                    )
                    now = time.monotonic()
                    if next_frame_at + self.frame_period < now:
                        next_frame_at = now
                if (
                    not isinstance(result, Exception)
                    and (not result[0] or result[1] is None)
                ):
                    if self.file_source:
                        return
                    self._stop_event.wait(0.05)

        self._capture_thread = threading.Thread(
            target=read_frames,
            name=f"aeroguard-read-{self.camera_id}",
            daemon=True,
        )
        self._capture_thread.start()

    def _reconnect(self):
        if self.reopen_capture is None:
            return False
        try:
            old_capture = self.capture
            self.capture = None
            if old_capture is not None:
                self._release_capture(old_capture)
            if self._capture_thread is not None:
                self._capture_thread.join(timeout=0.25)
            if self._stop_event.is_set() or self.stop_requested():
                return False
            new_capture = self.reopen_capture()
            if self._stop_event.is_set() or self.stop_requested():
                self._release_capture(new_capture)
                return False
            self.capture = new_capture
            with self._release_lock:
                self._released_capture_ids.discard(id(self.capture))
            while True:
                try:
                    self._read_results.get_nowait()
                except queue.Empty:
                    break
            if not self.capture or not self.capture.isOpened():
                return False
            self._start_capture_thread()
            return True
        except Exception as exc:
            self.error = exc
            logger.warning(
                "Camera source reconnect failed camera_id=%s error=%s",
                self.camera_id,
                type(exc).__name__,
            )
            return False

    def _run(self):
        last_frame_received_at = time.monotonic()
        reconnect_attempts = 0
        consecutive_read_failures = 0
        try:
            while not self._stop_event.is_set():
                if self.stop_requested():
                    return

                remaining = (
                    last_frame_received_at
                    + self.no_frame_grace_seconds
                    - time.monotonic()
                )
                try:
                    capture, result = self._read_results.get(
                        timeout=max(0.01, min(0.05, remaining))
                    )
                except queue.Empty:
                    if remaining <= 0:
                        if reconnect_attempts >= MAX_RECONNECT_ATTEMPTS:
                            return
                        reconnect_attempts += 1
                        last_frame_received_at = time.monotonic()
                        if not self._reconnect():
                            self._stop_event.wait(
                                min(0.1 * (2 ** (reconnect_attempts - 1)), 1.0)
                            )
                    continue

                if capture is not self.capture:
                    continue
                if isinstance(result, Exception):
                    raise result
                if result is None:
                    ret, frame = False, None
                else:
                    ret, frame = result

                if self._stop_event.is_set() or self.stop_requested():
                    return

                now = time.monotonic()
                if ret and frame is not None and getattr(frame, "size", 0) > 0:
                    capture_timestamp_ns = time.monotonic_ns()
                    metadata = {
                        "capture_timestamp_ns": capture_timestamp_ns,
                        "capture_clock": "backend_monotonic_after_decode",
                        "source_pts": None,
                        "source_rtp_timestamp": None,
                        "scheduler_queue_entry_ns": time.monotonic_ns(),
                        "captured_at": now,
                    }
                    self.frame_buffer.publish(frame, now, metadata)
                    self.on_frame(frame, now)
                    last_frame_received_at = now
                    reconnect_attempts = 0
                    consecutive_read_failures = 0
                    continue

                consecutive_read_failures += 1
                if self.file_source:
                    frame_count = int(
                        self.capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0
                    )
                    frame_position = int(
                        self.capture.get(cv2.CAP_PROP_POS_FRAMES) or 0
                    )
                    if (
                        (frame_count > 0 and frame_position >= frame_count)
                        or consecutive_read_failures >= 3
                    ):
                        return
                    self._stop_event.wait(0.1)
                    continue

                remaining = (
                    last_frame_received_at
                    + self.no_frame_grace_seconds
                    - now
                )
                if remaining <= 0:
                    if reconnect_attempts >= MAX_RECONNECT_ATTEMPTS:
                        return
                    reconnect_attempts += 1
                    last_frame_received_at = now
                    if not self._reconnect():
                        self._stop_event.wait(
                            min(0.1 * (2 ** (reconnect_attempts - 1)), 1.0)
                        )
                self._stop_event.wait(0.05)
        except Exception as exc:
            self.error = exc
            logger.exception(
                "Camera capture reader failed camera_id=%s error=%s",
                self.camera_id,
                type(exc).__name__,
            )
        finally:
            if self.capture is not None:
                self._release_capture(self.capture)
            self._done_event.set()
