import os
import threading
from urllib.parse import urlsplit

import cv2


LIVE_SOURCE_SCHEMES = {"http", "https", "rtmp", "rtsp", "rtsps"}
RTSP_TIMEOUT_SECONDS = 10
_CAPTURE_OPEN_LOCK = threading.RLock()
_FFMPEG_CAPTURE_OPTIONS = "OPENCV_FFMPEG_CAPTURE_OPTIONS"
_RTSP_TCP_OPTIONS = "rtsp_transport;tcp"


class RTSPCaptureError(RuntimeError):
    def __init__(self, category: str):
        self.category = category
        super().__init__(category)


class CameraSourceError(ValueError):
    pass


def resolve_camera_source(camera_type: str, stream_url: str | None) -> tuple[str, str | int]:
    source_type = (camera_type or "").strip().upper()
    source = (stream_url or "").strip()
    scheme = urlsplit(source).scheme.lower()

    if source_type in {"LIVE", "NVR"}:
        if scheme not in {"rtsp", "rtsps"} or not urlsplit(source).netloc:
            raise CameraSourceError(
                f"{source_type} cameras require a valid RTSP source"
            )
        return "rtsp", source

    if source_type == "USB":
        device_index = source or "0"
        if not device_index.isdigit():
            raise CameraSourceError("USB cameras require a numeric device index")
        return "device", int(device_index)

    if source_type == "UPLOAD":
        if not source or source == "FILE_UPLOADED" or not is_file_source(source):
            raise CameraSourceError("Uploaded cameras require a valid video file")
        return "file", source

    raise CameraSourceError(f"Unsupported camera source type: {source_type or 'unknown'}")


def is_file_source(source) -> bool:
    if not isinstance(source, str) or source.isdigit():
        return False
    return urlsplit(source).scheme.lower() not in LIVE_SOURCE_SCHEMES


def classify_capture_error(error: Exception) -> str:
    message = str(error).lower()
    if any(
        marker in message
        for marker in (
            "backend is not available",
            "not implemented",
            "unsupported",
            "bad argument",
        )
    ):
        return "backend_unavailable"
    if any(token in message for token in ("timed out", "timeout", "timedout")):
        return "connection_timeout"
    if any(
        marker in message
        for marker in ("server returned", "rtsp response", "http response")
    ):
        if "401" in message:
            return "authentication_rejected"
        if "403" in message:
            return "authorization_rejected"
    return "open_failed"


def open_capture(
    capture,
    source,
    backend=None,
    timeout_seconds=RTSP_TIMEOUT_SECONDS,
):
    if not hasattr(capture, "open"):
        return True

    scheme = urlsplit(source).scheme.lower() if isinstance(source, str) else ""
    is_rtsp = scheme in {"rtsp", "rtsps"}
    with _CAPTURE_OPEN_LOCK:
        original_options = os.environ.get(_FFMPEG_CAPTURE_OPTIONS)
        try:
            if is_rtsp:
                timeout_ms = int(timeout_seconds * 1000)
                parameters = [
                    cv2.CAP_PROP_OPEN_TIMEOUT_MSEC,
                    timeout_ms,
                    cv2.CAP_PROP_READ_TIMEOUT_MSEC,
                    timeout_ms,
                ]
                os.environ[_FFMPEG_CAPTURE_OPTIONS] = _RTSP_TCP_OPTIONS
                try:
                    return capture.open(
                        source,
                        cv2.CAP_FFMPEG,
                        parameters,
                    )
                except (AttributeError, TypeError, cv2.error) as exc:
                    raise RTSPCaptureError(
                        classify_capture_error(exc)
                    ) from None

            if backend is None:
                return capture.open(source)
            return capture.open(source, backend)
        finally:
            if original_options is None:
                os.environ.pop(_FFMPEG_CAPTURE_OPTIONS, None)
            else:
                os.environ[_FFMPEG_CAPTURE_OPTIONS] = original_options


def open_live_capture(capture, source, timeout_seconds=RTSP_TIMEOUT_SECONDS):
    return open_capture(capture, source, timeout_seconds=timeout_seconds)
