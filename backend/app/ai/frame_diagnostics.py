import hashlib
import json
import logging
import os
import queue
import tempfile
import threading
import time
import uuid
from pathlib import Path

import cv2
import numpy as np


logger = logging.getLogger(__name__)
MAX_DIAGNOSTIC_FRAMES = 3
_QUEUE_CAPACITY = 32
_SHUTDOWN_TIMEOUT_SECONDS = 5
_STAGES = {"A", "B", "C", "D", "E", "F", "G"}


class FrameDiagnostics:
    def __init__(self, camera_id: str, output_dir: Path):
        if not camera_id:
            raise ValueError("A diagnostic camera identifier is required")
        resolved_output = output_dir.expanduser().resolve()
        repository_root = Path(__file__).resolve().parents[3]
        try:
            resolved_output.relative_to(repository_root)
        except ValueError:
            pass
        else:
            raise ValueError("Diagnostic output must be outside the repository")

        self._camera_id = str(camera_id)
        self._camera_hash = hashlib.sha256(
            self._camera_id.encode("utf-8")
        ).hexdigest()[:16]
        self._output_dir = resolved_output / f"run-{uuid.uuid4().hex}"
        self._output_dir.mkdir(parents=True, exist_ok=False)
        self._queue = queue.Queue(maxsize=_QUEUE_CAPACITY)
        self._lock = threading.Lock()
        self._frame_count = 0
        self._sequence = 0
        self._queued_stages = set()
        self._closed = False
        self._worker = threading.Thread(
            target=self._write_events,
            name="aeroguard-frame-diagnostics",
            daemon=True,
        )
        self._worker.start()

    @classmethod
    def from_environment(cls):
        if os.getenv("AEROGUARD_FRAME_DIAGNOSTICS") != "1":
            return None

        camera_id = os.getenv("AEROGUARD_FRAME_DIAGNOSTICS_CAMERA_ID", "")
        configured_dir = os.getenv("AEROGUARD_FRAME_DIAGNOSTICS_DIR")
        output_dir = (
            Path(configured_dir)
            if configured_dir
            else Path(tempfile.gettempdir()) / "aeroguard-frame-diagnostics"
        )
        if configured_dir and not output_dir.is_absolute():
            raise ValueError("Diagnostic output directory must be absolute")
        return cls(camera_id, output_dir)

    def begin_frame(self, camera_id: str, frame, capture_timestamp_ns: int):
        if str(camera_id) != self._camera_id:
            return None
        with self._lock:
            if self._closed or self._frame_count >= MAX_DIAGNOSTIC_FRAMES:
                return None
            self._frame_count += 1
            self._sequence += 1
            sequence = self._sequence
        self.record_frame(
            camera_id,
            sequence,
            "A",
            frame,
            capture_timestamp_ns,
        )
        return sequence

    def record_frame(
        self,
        camera_id: str,
        sequence: int | None,
        stage: str,
        frame,
        capture_timestamp_ns: int,
    ) -> None:
        if (
            sequence is None
            or str(camera_id) != self._camera_id
            or stage not in _STAGES - {"G"}
            or frame is None
            or getattr(frame, "size", 0) <= 0
            or len(getattr(frame, "shape", ())) != 3
        ):
            return
        event = {
            "kind": "frame",
            "sequence": sequence,
            "stage": stage,
            "timestamp_monotonic_ns": time.monotonic_ns(),
            "capture_timestamp_monotonic_ns": capture_timestamp_ns,
            "frame": frame.copy(),
        }
        self._enqueue(event)

    def record_jpeg(
        self,
        camera_id: str,
        sequence: int | None,
        payload: bytes,
        capture_timestamp_ns: int,
    ) -> None:
        if sequence is None or str(camera_id) != self._camera_id:
            return
        self._enqueue(
            {
                "kind": "jpeg",
                "sequence": sequence,
                "stage": "G",
                "timestamp_monotonic_ns": time.monotonic_ns(),
                "capture_timestamp_monotonic_ns": capture_timestamp_ns,
                "payload": payload,
            }
        )

    def record_timing(
        self,
        camera_id: str,
        sequence: int,
        timings: dict,
    ) -> None:
        if str(camera_id) != self._camera_id:
            return
        self._enqueue(
            {
                "kind": "timing",
                "sequence": sequence,
                "stage": "timing",
                "timestamp_monotonic_ns": time.monotonic_ns(),
                "timings": timings,
            }
        )

    def _enqueue(self, event) -> None:
        with self._lock:
            if self._closed:
                return
            stage_key = (event["sequence"], event["stage"])
            if stage_key in self._queued_stages:
                return
            self._queued_stages.add(stage_key)
            try:
                self._queue.put_nowait(event)
            except queue.Full:
                logger.warning(
                    "Frame diagnostic queue full; dropping sample camera_hash=%s stage=%s",
                    self._camera_hash,
                    event["stage"],
                )

    def _write_events(self) -> None:
        manifest_path = self._output_dir / "frames.jsonl"
        while True:
            event = self._queue.get()
            try:
                if event is None:
                    return
                self._write_event(manifest_path, event)
            except Exception:
                logger.exception(
                    "Frame diagnostic write failed camera_hash=%s",
                    self._camera_hash,
                )
            finally:
                if event is not None:
                    with self._lock:
                        self._queued_stages.discard(
                            (event["sequence"], event["stage"])
                        )
                self._queue.task_done()

    def _write_event(self, manifest_path: Path, event) -> None:
        sequence = event["sequence"]
        stage = event["stage"]
        if event["kind"] == "timing":
            record = {
                "sequence": sequence,
                "stage": stage,
                "timestamp_monotonic_ns": event["timestamp_monotonic_ns"],
                "camera_hash": self._camera_hash,
                "timings": event["timings"],
            }
            with manifest_path.open("a", encoding="utf-8") as manifest:
                manifest.write(json.dumps(record, sort_keys=True) + "\n")
            return
        if event["kind"] == "jpeg":
            payload = event["payload"]
            decoded = cv2.imdecode(
                np.frombuffer(payload, dtype=np.uint8),
                cv2.IMREAD_COLOR,
            )
            height, width, channels = (
                decoded.shape if decoded is not None else (None, None, None)
            )
            metadata = {
                "width": int(width) if width is not None else None,
                "height": int(height) if height is not None else None,
                "dtype": str(decoded.dtype) if decoded is not None else None,
                "channels": int(channels) if channels is not None else None,
                "contiguous": (
                    bool(decoded.flags.c_contiguous)
                    if decoded is not None
                    else None
                ),
                "jpeg_encode_success": payload.startswith(b"\xff\xd8")
                and payload.endswith(b"\xff\xd9"),
                "jpeg_bytes": len(payload),
                "jpeg_decode_success": decoded is not None,
                "decoded_dimensions": (
                    [int(decoded.shape[1]), int(decoded.shape[0])]
                    if decoded is not None
                    else None
                ),
            }
            filename = f"camera-{self._camera_hash}-frame-{sequence:06d}-G.jpg"
            (self._output_dir / filename).write_bytes(payload)
        else:
            frame = event.pop("frame")
            height, width, channels = frame.shape
            encoded, buffer = cv2.imencode(
                ".jpg",
                frame,
                [int(cv2.IMWRITE_JPEG_QUALITY), 95],
            )
            payload = buffer.tobytes() if encoded else b""
            decoded = (
                cv2.imdecode(
                    np.frombuffer(payload, dtype=np.uint8),
                    cv2.IMREAD_COLOR,
                )
                if payload
                else None
            )
            metadata = {
                "width": int(width),
                "height": int(height),
                "dtype": str(frame.dtype),
                "channels": int(channels),
                "contiguous": bool(frame.flags.c_contiguous),
                "jpeg_encode_success": bool(encoded),
                "jpeg_bytes": len(payload),
                "jpeg_decode_success": decoded is not None,
                "decoded_dimensions": (
                    [int(decoded.shape[1]), int(decoded.shape[0])]
                    if decoded is not None
                    else None
                ),
            }
            filename = (
                f"camera-{self._camera_hash}-frame-{sequence:06d}-{stage}.jpg"
            )
            if encoded:
                (self._output_dir / filename).write_bytes(payload)

        record = {
            "sequence": sequence,
            "stage": stage,
            "timestamp_monotonic_ns": event["timestamp_monotonic_ns"],
            "capture_timestamp_monotonic_ns": event[
                "capture_timestamp_monotonic_ns"
            ],
            "camera_hash": self._camera_hash,
            "file": filename if metadata.get("jpeg_encode_success") else None,
            **metadata,
        }
        with manifest_path.open("a", encoding="utf-8") as manifest:
            manifest.write(json.dumps(record, sort_keys=True) + "\n")

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
        try:
            self._queue.put(None, timeout=_SHUTDOWN_TIMEOUT_SECONDS)
        except queue.Full:
            logger.warning(
                "Frame diagnostic queue did not drain before shutdown camera_hash=%s",
                self._camera_hash,
            )
            return
        self._worker.join(timeout=_SHUTDOWN_TIMEOUT_SECONDS)
        if self._worker.is_alive():
            logger.warning(
                "Frame diagnostic worker did not stop before shutdown camera_hash=%s",
                self._camera_hash,
            )

    @property
    def output_dir(self) -> Path:
        return self._output_dir
