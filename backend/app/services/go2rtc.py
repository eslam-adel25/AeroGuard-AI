import json
import logging
import os
import subprocess
import threading
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen


logger = logging.getLogger(__name__)

DEFAULT_GO2RTC_BASE_URL = "http://127.0.0.1:1984"
DEFAULT_GO2RTC_RTSP_URL = "rtsp://127.0.0.1:8556"
GO2RTC_STARTUP_TIMEOUT_SECONDS = 10
GO2RTC_REQUEST_TIMEOUT_SECONDS = 2
MSE_CODECS = (
    "avc1.640029,avc1.64002A,avc1.640033,"
    "mp4a.40.2,mp4a.40.5,flac,opus"
)


class Go2RTCError(RuntimeError):
    pass


def _backend_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _go2rtc_enabled() -> bool:
    return (os.getenv("GO2RTC_ENABLED") or "true").strip().lower() not in {
        "0",
        "false",
        "no",
    }


def build_go2rtc_base_url() -> str:
    configured = (os.getenv("GO2RTC_BASE_URL") or "").strip()
    return (configured or DEFAULT_GO2RTC_BASE_URL).rstrip("/")


def build_go2rtc_rtsp_url() -> str:
    configured = (os.getenv("GO2RTC_RTSP_URL") or "").strip()
    return (configured or DEFAULT_GO2RTC_RTSP_URL).rstrip("/")


def build_go2rtc_source_name(camera_id) -> str:
    name = str(camera_id).strip()
    if not name or any(char in name for char in "\r\n"):
        raise ValueError("A valid camera ID is required for a go2rtc stream name")
    return name


def build_go2rtc_source_url(camera_id, source_url: str | None = None) -> str:
    camera_key = quote(build_go2rtc_source_name(camera_id), safe="")
    return f"{build_go2rtc_rtsp_url()}/{camera_key}"


def build_go2rtc_live_url(camera_id, source_url: str | None = None) -> str:
    camera_key = build_go2rtc_source_name(camera_id)
    parts = urlsplit(build_go2rtc_base_url())
    query = urlencode({"src": camera_key})
    return urlunsplit(
        (parts.scheme, parts.netloc, f"{parts.path.rstrip('/')}/api/stream.m3u8", query, "")
    )


def build_go2rtc_webrtc_url(camera_id, source_url: str | None = None) -> str:
    camera_key = build_go2rtc_source_name(camera_id)
    parts = urlsplit(build_go2rtc_base_url())
    scheme = "wss" if parts.scheme == "https" else "ws"
    return urlunsplit(
        (
            scheme,
            parts.netloc,
            f"{parts.path.rstrip('/')}/api/ws",
            urlencode({"src": camera_key}),
            "",
        )
    )


def resolve_live_pipeline_url(camera_id, source_url: str | None = None) -> str | None:
    if not _go2rtc_enabled():
        return None
    return build_go2rtc_webrtc_url(camera_id, source_url)


def redact_go2rtc_source(source_url: str | None) -> str | None:
    if not source_url:
        return source_url
    parts = urlsplit(source_url)
    if not parts.scheme:
        return source_url
    host = parts.hostname or ""
    netloc = f"{host}:{parts.port}" if parts.port else host
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


class Go2RTCService:
    def __init__(self):
        self._lock = threading.RLock()
        self._process = None
        self._log_handle = None

    @property
    def executable_path(self) -> Path:
        configured = (os.getenv("GO2RTC_EXECUTABLE") or "").strip()
        if configured:
            return Path(configured).expanduser().resolve()
        executable = "go2rtc.exe" if os.name == "nt" else "go2rtc"
        return _backend_root() / "tools" / executable

    @property
    def config_path(self) -> Path:
        configured = (os.getenv("GO2RTC_CONFIG_PATH") or "").strip()
        if configured:
            return Path(configured).expanduser().resolve()
        return _backend_root() / "config" / "go2rtc.yaml"

    def _api_url(self, path: str) -> str:
        parts = urlsplit(build_go2rtc_base_url())
        return urlunsplit(
            (parts.scheme, parts.netloc, f"{parts.path.rstrip('/')}{path}", "", "")
        )

    def _request(self, method: str, path: str, query=None):
        url = self._api_url(path)
        if query:
            url = f"{url}?{urlencode(query)}"
        request = Request(
            url,
            data=b"" if method in {"PUT", "PATCH"} else None,
            headers={"Accept": "application/json"},
            method=method,
        )
        try:
            with urlopen(request, timeout=GO2RTC_REQUEST_TIMEOUT_SECONDS) as response:
                body = response.read()
        except HTTPError as exc:
            raise Go2RTCError(
                f"go2rtc API returned HTTP {exc.code} for {method} {path}"
            ) from None
        except (URLError, TimeoutError, OSError):
            raise Go2RTCError("go2rtc API is unreachable") from None
        if not body:
            return None
        try:
            return json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise Go2RTCError("go2rtc API returned an invalid response") from None

    def _get_streams_if_ready(self):
        try:
            streams = self._request("GET", "/api/streams")
        except Go2RTCError:
            return None
        return streams if isinstance(streams, dict) else None

    def is_available(self) -> bool:
        return self._get_streams_if_ready() is not None

    def start(self) -> None:
        with self._lock:
            if self.is_available():
                return

            executable = self.executable_path
            config = self.config_path
            if not executable.is_file():
                raise Go2RTCError(
                    f"go2rtc executable not found at {executable}; run backend/scripts/install_go2rtc.ps1"
                )
            if not config.is_file():
                raise Go2RTCError(f"go2rtc configuration not found at {config}")
            if self._process is not None and self._process.poll() is None:
                deadline = time.monotonic() + GO2RTC_STARTUP_TIMEOUT_SECONDS
                while time.monotonic() < deadline:
                    if self.is_available():
                        return
                    if self._process.poll() is not None:
                        break
                    time.sleep(0.2)
                raise Go2RTCError(
                    "the managed go2rtc process is running but its API is unavailable; check backend/logs/go2rtc.log"
                )
            if self._process is not None:
                self._process = None
                self._close_log_handle()

            log_path = _backend_root() / "logs" / "go2rtc.log"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            self._log_handle = log_path.open("a", encoding="utf-8")
            creation_flags = (
                getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
            )
            try:
                self._process = subprocess.Popen(
                    [str(executable), "-config", str(config)],
                    cwd=str(config.parent),
                    stdout=self._log_handle,
                    stderr=subprocess.STDOUT,
                    creationflags=creation_flags,
                )
            except OSError:
                self._close_log_handle()
                raise Go2RTCError("go2rtc could not be started") from None

            deadline = time.monotonic() + GO2RTC_STARTUP_TIMEOUT_SECONDS
            while time.monotonic() < deadline:
                if self.is_available():
                    logger.info("go2rtc service is available at %s", build_go2rtc_base_url())
                    return
                if self._process.poll() is not None:
                    break
                time.sleep(0.2)

            return_code = self._process.poll()
            self._stop_owned_process()
            if return_code is None:
                raise Go2RTCError(
                    "go2rtc did not become available before the startup timeout; check backend/logs/go2rtc.log and configured ports"
                )
            raise Go2RTCError(
                f"go2rtc exited during startup with code {return_code}; check backend/logs/go2rtc.log and configured ports"
            )

    def register_stream(self, camera_id, source_url: str) -> None:
        with self._lock:
            self.start()
            name = build_go2rtc_source_name(camera_id)
            streams = self._request("GET", "/api/streams")
            if not isinstance(streams, dict):
                raise Go2RTCError("go2rtc stream list response is invalid")
            existing_streams = streams.get("streams", streams)
            method = "PATCH" if name in existing_streams else "PUT"
            self._request(
                method,
                "/api/streams",
                {"src": source_url, "name": name},
            )
            logger.info("Registered camera stream with go2rtc camera_id=%s", name)

    def remove_stream(self, camera_id) -> None:
        with self._lock:
            self.start()
            name = build_go2rtc_source_name(camera_id)
            streams = self._request("GET", "/api/streams")
            if not isinstance(streams, dict):
                raise Go2RTCError("go2rtc stream list response is invalid")
            existing_streams = streams.get("streams", streams)
            if name not in existing_streams:
                return
            self._request("DELETE", "/api/streams", {"src": name})
            logger.info("Removed camera stream from go2rtc camera_id=%s", name)

    def _close_log_handle(self) -> None:
        if self._log_handle is not None:
            self._log_handle.close()
            self._log_handle = None

    def _stop_owned_process(self) -> None:
        process = self._process
        self._process = None
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        self._close_log_handle()

    def stop(self) -> None:
        with self._lock:
            self._stop_owned_process()


go2rtc_service = Go2RTCService()
