import cv2
import asyncio
import time
import os
import threading
import math
import logging
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import torch
from ultralytics import YOLO
from ultralytics.nn import tasks as ultralytics_tasks
from sqlalchemy.orm import Session
from ..database.session import SessionLocal
from ..models.models import Detection, Camera, RestrictedZone, UserSettings
from ..repositories.detection_repository import DetectionRepository
from ..services.decision_engine import DecisionEngine
from ..services.camera_status import CAMERA_NO_FRAME_GRACE_SECONDS
from ..websocket.manager import manager
from .identity import PersonIdentityRegistry
from .tracker import TrackerManager
from ..services.ai_service import AIService
from .ownership_config import (
    OWNERSHIP_ASSIGNMENT_REQUIRED_FRAMES,
    OWNERSHIP_LOSS_REQUIRED_FRAMES,
    OWNERSHIP_MAX_DISTANCE_PX,
    UNATTENDED_TIMEOUT_SECONDS,
)

logger = logging.getLogger(__name__)
FIRE_SMOKE_MODEL_DEFAULT_PATH = "models/fire-smoke-yolov8n.pt"
GENERAL_DETECTION_LABELS = {
    "person",
    "bag",
    "suitcase",
    "backpack",
    "car",
    "truck",
    "bus",
    "motorcycle",
    "bicycle",
    "vehicle",
}
SPECIALIST_DETECTION_LABELS = {"fire", "smoke"}
VEHICLE_DETECTION_LABELS = {
    "car",
    "truck",
    "bus",
    "motorcycle",
    "bicycle",
    "vehicle",
}


def _get_detection_persistence_label(label_name):
    if label_name == "person":
        return "Person"
    if label_name in VEHICLE_DETECTION_LABELS:
        return label_name
    return "Baggage"


def build_detection_record(camera_id, owner_id, detection_type, confidence, status=None):
    priority = "Medium"
    is_violation = False
    violation_type = None

    if status == "DANGER":
        priority = "Critical"
        is_violation = True
        violation_type = "DANGER"
    elif status == "WARNING":
        priority = "High"
        is_violation = True
        violation_type = "WARNING"

    return Detection(
        camera_id=camera_id,
        owner_id=owner_id,
        detection_type=detection_type,
        confidence=float(confidence or 0),
        priority=priority,
        is_violation=is_violation,
        violation_type=violation_type,
    )


def _build_empty_model_result():
    class EmptyBoxes:
        xyxy = []
        cls = []
        conf = []

        def __len__(self):
            return 0

    class EmptyResult:
        boxes = EmptyBoxes()

    return [EmptyResult()]


def _get_source_frame_period(capture, is_file_source):
    if not is_file_source:
        return None
    source_fps = float(capture.get(cv2.CAP_PROP_FPS) or 0)
    if not math.isfinite(source_fps) or source_fps <= 0:
        return None
    return 1.0 / source_fps


def _normalize_zone_coords(raw_coords, camera_id=None, annotation_id=None, rule_type=None):
    """Normalize zone coordinates so all rule checks receive a plain coordinate list."""
    if isinstance(raw_coords, dict):
        points = raw_coords.get("points")
        if isinstance(points, list):
            normalized = []
            for point in points:
                if isinstance(point, (list, tuple)) and len(point) >= 2:
                    normalized.append([float(point[0]), float(point[1])])
                else:
                    raise ValueError(
                        f"Invalid coordinate point in zone annotation: camera={camera_id} annotation={annotation_id} rule={rule_type} point={point!r}"
                    )
            return normalized
        raise ValueError(
            f"Invalid wrapped zone payload: camera={camera_id} annotation={annotation_id} rule={rule_type} payload={raw_coords!r}"
        )

    if isinstance(raw_coords, list):
        return raw_coords

    raise ValueError(
        f"Unsupported zone coordinate format: camera={camera_id} annotation={annotation_id} rule={rule_type} value={raw_coords!r}"
    )


def _line_coords_in_frame(coords, frame_shape):
    """Convert normalized annotation points to the processor frame coordinate system."""
    line_coords = np.asarray(coords, dtype=np.float32)
    if line_coords.size and np.all(line_coords >= 0.0) and np.all(line_coords <= 1.0):
        line_coords *= np.array([frame_shape[1], frame_shape[0]], dtype=np.float32)
    return line_coords


class AIProcessor:
    def __init__(self, model_path: str, fire_smoke_model_path: str | None = None):
        # تحميل الموديل لمرة واحدة عند التشغيل (صفحة 163)
        self.model_path = self._resolve_model_path(model_path)
        self._patch_ultralytics_weights_only()
        self.model = YOLO(self.model_path)
        self.fire_smoke_model_path = fire_smoke_model_path or os.getenv(
            "AEROGUARD_FIRE_SMOKE_MODEL_PATH",
            FIRE_SMOKE_MODEL_DEFAULT_PATH,
        )
        self.fire_smoke_model = None
        self.fire_smoke_class_map = {}
        self._model_lock = threading.Lock()
        self._load_fire_smoke_model()
        self.decision_engine = DecisionEngine()
        self.trackers = {}

        # مخازن الذاكرة الحية
        self.last_frames = {}
        self.last_alert_time = {}
        self.alert_persistence = {}
        self.object_history = {}
        self.loitering_tracker = {}  # camera_id -> {track_id: {first_seen, last_pos, last_move_time}}
        self.bag_tracker = {}  # camera_id -> {track_id: {first_seen, last_near_person_time}}
        self.crowd_cooldown = {}  # camera_id -> last_alert_time
        self.display_id_state = {}  # camera_id -> {internal_track_id: display_id}
        self.person_identity_registries = {}  # camera_id -> session-only person identities
        self.bag_owner_state = {}  # camera_id -> {bag_internal_id: owner_internal_id}
        self.bag_owner_person_state = {}  # camera_id -> {bag_internal_id: persistent_person_id}
        self.bag_owner_evidence = {}  # camera_id -> {bag_internal_id: {candidate_owner, confirm_streak, missing_streak, confirmed_owner}}
        self.bag_owner_status = {}  # camera_id -> {bag_internal_id: "owned" | "lost" | "unknown"}
        self.active_critical_alerts = {}  # camera_id -> [alert_timestamps]
        self._detection_persist_cooldown = {}  # key -> last persisted timestamp
        self._stop_flags = {}
        self._active_cameras = set()
        self._starting_cameras = set()
        self._camera_started_at = {}
        self._last_frame_received_at = {}
        self._active_camera_lock = threading.Lock()
        self._active_alarm_state = {}  # camera_id -> bool
        self._active_alarm_sources = {}  # camera_id -> list[str]
        self._settings_by_owner = {}
        self._settings_lock = threading.Lock()

    def _load_fire_smoke_model(self):
        """Load the optional specialist model without blocking general detection."""
        try:
            model_path = self._resolve_model_path(self.fire_smoke_model_path)
            model = YOLO(model_path)
            class_map = self._build_fire_smoke_class_map(model.names)
            if not SPECIALIST_DETECTION_LABELS.issubset(class_map.values()):
                raise ValueError(
                    "Fire/smoke model must expose both fire and smoke classes"
                )
            self.fire_smoke_model = model
            self.fire_smoke_model_path = model_path
            self.fire_smoke_class_map = class_map
            logger.info(
                "Loaded fire/smoke model from %s with classes %s",
                model_path,
                class_map,
            )
        except Exception as exc:
            self.fire_smoke_model = None
            self.fire_smoke_class_map = {}
            logger.error(
                "Fire/smoke specialist model unavailable; general detection remains active: %s: %s",
                type(exc).__name__,
                exc,
            )

    @staticmethod
    def _build_fire_smoke_class_map(model_names):
        names = model_names.values() if isinstance(model_names, dict) else model_names
        class_map = {}
        for class_id, name in enumerate(names):
            canonical_name = str(name).strip().lower()
            if canonical_name in SPECIALIST_DETECTION_LABELS:
                class_map[class_id] = canonical_name
        return class_map

    def _resolve_model_path(self, model_path: str) -> str:
        """Resolve a backend-relative model path to an absolute filesystem path."""
        path = Path(model_path)
        if path.is_absolute():
            resolved = path
        else:
            backend_root = Path(__file__).resolve().parents[2]
            resolved = backend_root / path

        if not resolved.exists():
            raise FileNotFoundError(f"YOLO model file not found: {resolved}")
        if resolved.stat().st_size == 0:
            raise ValueError(f"YOLO model file is empty: {resolved}")
        return str(resolved)

    @staticmethod
    def _bbox_intersects_polygon(bbox, polygon) -> bool:
        x1, y1, x2, y2 = bbox
        if x1 >= x2 or y1 >= y2 or polygon is None or polygon.size == 0:
            return False

        corners = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
        for corner in corners:
            if cv2.pointPolygonTest(polygon, corner, False) >= 0:
                return True

        polygon_points = polygon.reshape(-1, 2)
        for px, py in polygon_points:
            if x1 <= px <= x2 and y1 <= py <= y2:
                return True

        rect = (int(x1), int(y1), int(x2 - x1), int(y2 - y1))
        for i in range(len(polygon_points)):
            p1 = tuple(map(int, polygon_points[i]))
            p2 = tuple(map(int, polygon_points[(i + 1) % len(polygon_points)]))
            if cv2.clipLine(rect, p1, p2)[0]:
                return True

        return False

    def _patch_ultralytics_weights_only(self):
        """Patch installed Ultralytics to make torch.load use weights_only=False for this backend."""
        try:
            if hasattr(ultralytics_tasks, 'torch_safe_load'):
                # Patch the internal safe load function if needed for older ultralytics installs.
                def patched_torch_safe_load(weight):
                    from ultralytics.utils.downloads import attempt_download_asset
                    from ultralytics.utils.checks import check_suffix

                    check_suffix(file=weight, suffix='.pt')
                    file = attempt_download_asset(weight)
                    try:
                        with ultralytics_tasks.temporary_modules({
                            'ultralytics.yolo.utils': 'ultralytics.utils',
                            'ultralytics.yolo.v8': 'ultralytics.models.yolo',
                            'ultralytics.yolo.data': 'ultralytics.data',
                        }):
                            return torch.load(file, map_location='cpu', weights_only=False), file
                    except Exception:
                        return ultralytics_tasks.torch_safe_load(weight)

                ultralytics_tasks.torch_safe_load = patched_torch_safe_load
        except Exception:
            pass

    def _get_active_critical_alert_count(self, camera_id) -> int:
        camera_key = str(camera_id)
        now = time.time()
        alerts = self.active_critical_alerts.get(camera_key, [])
        active = [ts for ts in alerts if now - ts < 5]
        self.active_critical_alerts[camera_key] = active
        return len(active)

    async def _broadcast_alarm_state(
        self,
        camera_id,
        active,
        sources=None,
        audience_user_id=None,
    ):
        try:
            await manager.broadcast({
                "event": "alarm_state",
                "data": {
                    "camera_id": str(camera_id),
                    "active": bool(active),
                    "sources": sorted(sources) if sources else [],
                },
            }, audience_user_id=str(audience_user_id) if audience_user_id else None)
        except Exception:
            pass

    def _register_critical_alert(self, camera_id) -> None:
        camera_key = str(camera_id)
        alerts = self.active_critical_alerts.setdefault(camera_key, [])
        alerts.append(time.time())
        now = time.time()
        self.active_critical_alerts[camera_key] = [ts for ts in alerts if now - ts < 5]

    async def _register_persistent_alert(
        self,
        ai_service,
        camera_id,
        alert_key,
        detection_type,
        severity,
        confidence,
        track_id,
        owner_id,
        metadata,
        annotated_frame,
        active_alert_keys,
        capture_screenshot=False,
    ):
        active_alert_keys.add(alert_key)
        now = time.monotonic()
        state = self.alert_persistence.get(alert_key)

        if state is None:
            if time.time() - self.last_alert_time.get(alert_key, 0) <= 5:
                return
            state = {
                "started_at": now,
                "finalized": False,
            }
            self.alert_persistence[alert_key] = state

        if (
            not capture_screenshot
            or state["finalized"]
            or now - state["started_at"] < 5
        ):
            return

        screenshot_bytes = None
        try:
            encoded, jpg = cv2.imencode(".jpg", annotated_frame)
            if encoded:
                screenshot_bytes = jpg.tobytes()
            else:
                print(f"⚠️ [{camera_id}] alert screenshot encoding returned no image")
        except Exception as exc:
            print(
                f"⚠️ [{camera_id}] alert screenshot encoding failed: "
                f"{type(exc).__name__}: {exc}"
            )

        event = ai_service.register_event(
            camera_id=camera_id,
            detection_type=detection_type,
            severity=severity,
            confidence=confidence,
            track_id=track_id,
            user_id=owner_id,
            metadata=metadata,
            screenshot_bytes=screenshot_bytes,
        )
        state["event_id"] = str(event.event_id)
        state["finalized"] = True
        state["screenshot_persisted"] = bool(event.screenshot_path)
        self.last_alert_time[alert_key] = time.time()

    def _reset_inactive_alert_persistence(self, camera_id, active_alert_keys):
        prefix = f"{camera_id}_"
        for alert_key in list(self.alert_persistence):
            if alert_key.startswith(prefix) and alert_key not in active_alert_keys:
                self.alert_persistence.pop(alert_key, None)

    def _persist_detection(self, db_session, camera_id, owner_id, detection_type, confidence, track_id, status=None):
        if not owner_id:
            return None

        key = f"{str(camera_id)}:{str(track_id)}:{(detection_type or '').lower()}"
        now = time.time()
        last_persisted = self._detection_persist_cooldown.get(key, 0)
        if now - last_persisted < 5:
            return None

        self._detection_persist_cooldown[key] = now
        repo = DetectionRepository(db_session)
        detection = build_detection_record(
            camera_id=camera_id,
            owner_id=owner_id,
            detection_type=detection_type,
            confidence=confidence,
            status=status,
        )
        return repo.save_detection(detection)

    def update_config(self, settings_model: UserSettings):
        """تحديث إعدادات المحرك فور ضغط زر Save في صفحة Settings (Section 2)"""
        settings_snapshot = self._snapshot_camera_settings(settings_model)
        owner_id = settings_snapshot.owner_id
        if owner_id is not None:
            with self._settings_lock:
                self._settings_by_owner[str(owner_id)] = settings_snapshot
        print(f"⚙️ AI Engine updated with new settings: Conf={settings_snapshot.detection_confidence}")
        # adjust model device if GPU flag changed
        try:
            use_gpu = settings_snapshot.gpu_enabled
            dev = "cuda" if use_gpu else "cpu"
            # recreate model on requested device
            with self._model_lock:
                self.model = YOLO(self.model_path, device=dev)
                if self.fire_smoke_model is not None:
                    self.fire_smoke_model = YOLO(self.fire_smoke_model_path, device=dev)
            print(f"⚙️ AI Engine model reloaded on device={dev}")
        except Exception as exc:
            # ignore if device change not supported in environment
            print(f"⚠️ AI Engine model reload failed: {type(exc).__name__}: {exc}")

    @staticmethod
    def _snapshot_camera_settings(settings_model):
        field_names = (
            "owner_id",
            "detection_confidence",
            "max_objects",
            "gpu_enabled",
            "frame_skip",
            "restricted_area_enabled",
            "wrong_direction_enabled",
            "loitering_enabled",
            "loitering_seconds",
            "abandoned_bag_enabled",
            "abandoned_bag_seconds",
            "fire_detection_enabled",
            "smoke_detection_enabled",
        )
        return SimpleNamespace(
            **{
                field_name: getattr(settings_model, field_name, None)
                for field_name in field_names
            }
        )

    def _get_settings_for_owner(self, owner_id, fallback=None):
        if owner_id is None:
            return fallback
        with self._settings_lock:
            return self._settings_by_owner.get(str(owner_id), fallback)

    @staticmethod
    def _is_fire_smoke_enabled(label_name, camera_settings):
        fire_enabled = bool(
            getattr(camera_settings, "fire_detection_enabled", False)
        )
        smoke_enabled = bool(
            getattr(camera_settings, "smoke_detection_enabled", False)
        )
        return (
            (label_name == "fire" and fire_enabled)
            or (label_name == "flame" and fire_enabled)
            or (label_name == "smoke" and smoke_enabled)
        )

    def _predict_frame(self, frame, confidence_threshold):
        with self._model_lock:
            model = self.model
            return (
                model.predict(
                    frame,
                    conf=confidence_threshold,
                    verbose=False,
                ),
                model.names,
            )

    def _predict_fire_smoke_frame(self, frame, confidence_threshold):
        with self._model_lock:
            if self.fire_smoke_model is None:
                return _build_empty_model_result(), {}
            model = self.fire_smoke_model
            return (
                model.predict(
                    frame,
                    conf=confidence_threshold,
                    verbose=False,
                ),
                model.names,
            )

    @staticmethod
    def _extract_model_detections(results, model_names, allowed_labels, class_map=None):
        detections = []
        result = results[0] if results else None
        boxes_obj = getattr(result, "boxes", None) if result is not None else None
        if boxes_obj is None:
            return detections
        if not all(
            hasattr(boxes_obj, attribute)
            for attribute in ("xyxy", "cls", "conf")
        ):
            return detections

        boxes = boxes_obj.xyxy.cpu().numpy() if len(boxes_obj) else []
        labels = boxes_obj.cls.cpu().numpy().astype(int) if len(boxes_obj) else []
        confs = boxes_obj.conf.cpu().numpy() if len(boxes_obj) else []
        for box, class_id, confidence in zip(boxes, labels, confs):
            if class_map is not None:
                label_name = class_map.get(int(class_id))
            else:
                label_name = str(model_names[int(class_id)]).lower()
            if label_name not in allowed_labels:
                continue
            x1, y1, x2, y2 = box.astype(int)
            detections.append(
                {
                    "bbox": [int(x1), int(y1), int(x2), int(y2)],
                    "class_name": label_name,
                    "confidence": float(confidence),
                }
            )
        return detections

    @staticmethod
    def _bbox_iou(first_bbox, second_bbox):
        ax1, ay1, ax2, ay2 = first_bbox
        bx1, by1, bx2, by2 = second_bbox
        intersection_width = max(0, min(ax2, bx2) - max(ax1, bx1))
        intersection_height = max(0, min(ay2, by2) - max(ay1, by1))
        intersection = intersection_width * intersection_height
        if intersection == 0:
            return 0.0
        first_area = max(0, ax2 - ax1) * max(0, ay2 - ay1)
        second_area = max(0, bx2 - bx1) * max(0, by2 - by1)
        union = first_area + second_area - intersection
        return intersection / union if union else 0.0

    @classmethod
    def _merge_detections(cls, detections):
        merged = []
        for detection in sorted(
            detections,
            key=lambda item: item["confidence"],
            reverse=True,
        ):
            duplicate = any(
                detection["class_name"] == existing["class_name"]
                and cls._bbox_iou(detection["bbox"], existing["bbox"]) >= 0.5
                for existing in merged
            )
            if not duplicate:
                merged.append(detection)
        return merged

    def reserve_camera_start(self, camera_id):
        """Atomically reserve one camera's processing slot before scheduling its worker."""
        camera_key = str(camera_id)
        with self._active_camera_lock:
            if camera_key in self._active_cameras:
                return "stopping" if self._stop_flags.get(camera_key, False) else "active"
            if camera_key in self._starting_cameras:
                return "stopping" if self._stop_flags.get(camera_key, False) else "starting"
            self._active_cameras.add(camera_key)
            self._stop_flags[camera_key] = False
            self._camera_started_at[camera_key] = time.monotonic()
            self._last_frame_received_at.pop(camera_key, None)
            return "reserved"

    def reserve_camera_startup(self, camera_id):
        """Reserve a camera start without marking it as actively processing."""
        camera_key = str(camera_id)
        with self._active_camera_lock:
            if camera_key in self._active_cameras:
                return "stopping" if self._stop_flags.get(camera_key, False) else "active"
            if camera_key in self._starting_cameras:
                return "stopping" if self._stop_flags.get(camera_key, False) else "starting"
            self._starting_cameras.add(camera_key)
            self._stop_flags[camera_key] = False
            return "reserved"

    def activate_camera_startup(self, camera_id):
        """Promote a validated startup to active processing unless Stop cancelled it."""
        camera_key = str(camera_id)
        with self._active_camera_lock:
            if camera_key not in self._starting_cameras:
                return "cancelled"
            if self._stop_flags.get(camera_key, False):
                self._starting_cameras.discard(camera_key)
                self._stop_flags.pop(camera_key, None)
                return "cancelled"
            self._starting_cameras.remove(camera_key)
            self._active_cameras.add(camera_key)
            self._camera_started_at[camera_key] = time.monotonic()
            self._last_frame_received_at.pop(camera_key, None)
            return "reserved"

    def release_camera_startup(self, camera_id):
        """Release only a pending startup reservation."""
        camera_key = str(camera_id)
        with self._active_camera_lock:
            if camera_key in self._starting_cameras:
                self._starting_cameras.remove(camera_key)
                self._stop_flags.pop(camera_key, None)

    def release_camera_start(self, camera_id):
        """Release a reserved start if scheduling or setup fails before worker cleanup."""
        camera_key = str(camera_id)
        with self._active_camera_lock:
            self._stop_flags.pop(camera_key, None)
            self._active_cameras.discard(camera_key)
            self._starting_cameras.discard(camera_key)
            self._camera_started_at.pop(camera_key, None)
            self._last_frame_received_at.pop(camera_key, None)

    def _camera_stop_requested(self, camera_id):
        with self._active_camera_lock:
            return self._stop_flags.get(str(camera_id), False)

    def get_camera_runtime_statuses(self, camera_ids):
        with self._active_camera_lock:
            return {
                camera_key: {
                    "started_at": self._camera_started_at[camera_key],
                    "last_frame_at": self._last_frame_received_at.get(camera_key),
                    "stop_requested": self._stop_flags.get(camera_key, False),
                }
                for camera_key in map(str, camera_ids)
                if camera_key in self._active_cameras
                and camera_key in self._camera_started_at
            }

    def _record_frame_received(self, camera_id):
        with self._active_camera_lock:
            self._last_frame_received_at[str(camera_id)] = time.monotonic()

    @staticmethod
    def _consume_task_exception(task):
        if not task.cancelled():
            task.exception()

    @staticmethod
    def _release_capture_after_open(capture, camera_id, task):
        if task.cancelled():
            return
        error = task.exception()
        if error is not None:
            print(f"⚠️ [{camera_id}] delayed capture open failed: {type(error).__name__}: {error}")
        try:
            capture.release()
        except Exception as exc:
            print(f"⚠️ [{camera_id}] delayed capture release failed: {type(exc).__name__}: {exc}")

    async def _open_live_capture(self, capture, source, camera_id, deadline):
        open_task = asyncio.create_task(
            asyncio.to_thread(
                capture.open,
                source,
                cv2.CAP_DSHOW,
            )
            if source == 0
            else asyncio.to_thread(capture.open, source)
        )
        while True:
            remaining = deadline - time.monotonic()
            if self._camera_stop_requested(camera_id) or remaining <= 0:
                open_task.add_done_callback(
                    lambda task: self._release_capture_after_open(
                        capture,
                        camera_id,
                        task,
                    )
                )
                capture.release()
                return None

            try:
                done, _ = await asyncio.wait(
                    {open_task},
                    timeout=min(0.25, remaining),
                )
            except asyncio.CancelledError:
                open_task.add_done_callback(
                    lambda task: self._release_capture_after_open(
                        capture,
                        camera_id,
                        task,
                    )
                )
                raise
            if done:
                return bool(open_task.result() and capture.isOpened())

    async def _read_live_frame(self, capture, camera_id, deadline):
        while True:
            remaining = deadline - time.monotonic()
            if self._camera_stop_requested(camera_id) or remaining <= 0:
                capture.release()
                return None

            read_task = asyncio.create_task(asyncio.to_thread(capture.read))
            try:
                while not read_task.done():
                    remaining = deadline - time.monotonic()
                    if self._camera_stop_requested(camera_id) or remaining <= 0:
                        read_task.add_done_callback(self._consume_task_exception)
                        capture.release()
                        return None
                    await asyncio.wait(
                        {read_task},
                        timeout=min(0.05, remaining),
                    )
            except asyncio.CancelledError:
                read_task.add_done_callback(self._consume_task_exception)
                raise

            result = read_task.result()
            ret, frame = result
            if ret and frame is not None and getattr(frame, "size", 0) > 0:
                return result

            remaining = deadline - time.monotonic()
            if remaining > 0:
                await asyncio.sleep(min(0.25, remaining))

    def _initialize_camera_runtime_state(self, camera_id):
        camera_key = str(camera_id)
        camera_tracker = TrackerManager()
        camera_tracker.initialize()
        self.trackers[camera_key] = camera_tracker
        self.object_history[camera_key] = {}
        self.loitering_tracker[camera_key] = {}
        self.bag_tracker[camera_key] = {}
        self.display_id_state[camera_key] = {}
        self.person_identity_registries[camera_key] = PersonIdentityRegistry()
        self.bag_owner_state[camera_key] = {}
        self.bag_owner_person_state[camera_key] = {}
        self.bag_owner_evidence[camera_key] = {}
        self.bag_owner_status[camera_key] = {}
        self.active_critical_alerts[camera_key] = []
        self._active_alarm_state[camera_key] = False
        self._active_alarm_sources[camera_key] = []

    def _clear_camera_runtime_state(self, camera_id):
        camera_key = str(camera_id)
        self.last_frames.pop(camera_key, None)
        for state in (
            self.trackers,
            self.object_history,
            self.loitering_tracker,
            self.bag_tracker,
            self.display_id_state,
            self.person_identity_registries,
            self.bag_owner_state,
            self.bag_owner_person_state,
            self.bag_owner_evidence,
            self.bag_owner_status,
            self.active_critical_alerts,
            self.crowd_cooldown,
            self._active_alarm_state,
            self._active_alarm_sources,
        ):
            state.pop(camera_key, None)
        self._reset_inactive_alert_persistence(camera_key, set())

    def get_latest_frame(self, camera_id):
        return self.last_frames.get(str(camera_id))

    @staticmethod
    def _get_detection_box_color(label_name):
        """Return a fixed color for normal detections by class without using red."""
        normalized = (label_name or "").lower()
        if normalized in {"person"}:
            return (0, 255, 0)
        if normalized in {"bag", "backpack", "suitcase", "baggage", "luggage"}:
            return (0, 255, 255)
        if normalized in {"car", "bus", "truck", "motorcycle", "bicycle", "vehicle"}:
            return (255, 0, 0)
        if normalized in {"animal", "dog", "cat", "bird"}:
            return (0, 165, 255)
        if normalized in {"knife", "weapon", "gun"}:
            return (255, 0, 255)
        return (255, 255, 0)

    @staticmethod
    def _get_track_id(track) -> str | int | None:
        """Extract a stable track identifier from the tracker object if available."""
        if track is None:
            return None

        for attr_name in ("track_id", "id"):
            value = getattr(track, attr_name, None)
            if value is None:
                continue
            if isinstance(value, (str, int)):
                return value
            if hasattr(value, "__int__"):
                try:
                    return int(value)
                except (TypeError, ValueError):
                    pass

        tracked_object = getattr(track, "tracked_object", None)
        if tracked_object is not None:
            return AIProcessor._get_track_id(tracked_object)

        return None

    @staticmethod
    def _get_person_confidence_threshold(default_confidence):
        """Use a slightly lower threshold for person detections to improve recall without changing the model."""
        try:
            configured = float(default_confidence)
        except (TypeError, ValueError):
            configured = 0.5
        return max(0.25, min(0.5, configured - 0.12))

    def _assign_display_ids(self, camera_id, active_tracks):
        """Create visualization-only display IDs for currently visible tracks without changing tracker internals."""
        camera_key = str(camera_id)
        state = self.display_id_state.setdefault(camera_key, {})
        visible_ids = {track.track_id for track in active_tracks if getattr(track, "track_id", None) is not None}

        # Remove stale ids for tracks no longer visible.
        for internal_id in list(state.keys()):
            if internal_id not in visible_ids:
                del state[internal_id]

        ordered_tracks = [track for track in active_tracks if getattr(track, "track_id", None) is not None]
        ordered_tracks.sort(key=lambda track: (getattr(track, "bbox", [0, 0, 0, 0])[1], getattr(track, "bbox", [0, 0, 0, 0])[0]))

        display_map = {}
        for index, track in enumerate(ordered_tracks, start=1):
            internal_id = getattr(track, "track_id", None)
            if internal_id is None:
                continue
            display_map[internal_id] = index
            state[internal_id] = index

        # Keep any visible ids that are no longer part of the active set in state for the current frame.
        for internal_id in visible_ids:
            if internal_id not in display_map:
                display_map[internal_id] = state.get(internal_id, 0)

        return display_map

    def _assign_person_ids(self, camera_id, active_tracks, frame):
        camera_key = str(camera_id)
        registry = self.person_identity_registries.setdefault(
            camera_key,
            PersonIdentityRegistry(),
        )
        person_tracks = [
            track for track in active_tracks
            if getattr(track, "class_name", None) == "person"
        ]
        return registry.assign(person_tracks, frame)

    def _assign_bag_owner(self, camera_id, person_tracks, bag_tracks, person_ids=None):
        """Assign a stable owner ID to bags for overlay display without changing tracker internals."""
        camera_key = str(camera_id)
        bag_owner_state = getattr(self, "bag_owner_state", {}).setdefault(camera_key, {})
        bag_owner_person_state = getattr(self, "bag_owner_person_state", {}).setdefault(camera_key, {})
        bag_owner_evidence = getattr(self, "bag_owner_evidence", {}).setdefault(camera_key, {})
        bag_owner_status = getattr(self, "bag_owner_status", {}).setdefault(camera_key, {})
        person_ids = person_ids or {}
        now = time.time()

        person_candidates = []
        for track in person_tracks:
            bbox = getattr(track, "bbox", None)
            if bbox is None or len(bbox) != 4:
                continue
            person_candidates.append(track)

        visible_bag_ids = set()
        owner_map = {}
        for bag_track in bag_tracks:
            bag_id = getattr(bag_track, "track_id", None)
            if bag_id is None:
                continue

            visible_bag_ids.add(bag_id)
            evidence = bag_owner_evidence.setdefault(
                bag_id,
                {
                    "candidate_owner": None,
                    "confirm_streak": 0,
                    "missing_streak": 0,
                    "confirmed_owner": bag_owner_state.get(bag_id),
                    "confirmed_owner_person_id": bag_owner_person_state.get(bag_id),
                    "state": "unknown",
                    "state_started_at": None,
                },
            )

            best_owner = None
            best_score = None
            bag_bbox = getattr(bag_track, "bbox", None) or [0, 0, 0, 0]
            bag_center = [int((bag_bbox[0] + bag_bbox[2]) / 2), int((bag_bbox[1] + bag_bbox[3]) / 2)]
            for person_track in person_candidates:
                person_bbox = getattr(person_track, "bbox", None) or [0, 0, 0, 0]
                person_center = [int((person_bbox[0] + person_bbox[2]) / 2), int((person_bbox[1] + person_bbox[3]) / 2)]
                dx = bag_center[0] - person_center[0]
                dy = bag_center[1] - person_center[1]
                distance = (dx * dx + dy * dy) ** 0.5
                if distance > OWNERSHIP_MAX_DISTANCE_PX:
                    continue
                score = max(0.0, float(OWNERSHIP_MAX_DISTANCE_PX) - distance)
                if best_score is None or score > best_score:
                    best_score = score
                    best_owner = getattr(person_track, "track_id", None)

            confirmed_owner = evidence.get("confirmed_owner")
            if best_owner is None:
                evidence["missing_streak"] = int(evidence.get("missing_streak", 0)) + 1
                evidence["confirm_streak"] = 0
                if confirmed_owner is not None:
                    if evidence["missing_streak"] < OWNERSHIP_LOSS_REQUIRED_FRAMES:
                        evidence["state"] = "owned"
                        evidence["state_started_at"] = None
                        bag_owner_state[bag_id] = confirmed_owner
                        owner_map[bag_id] = confirmed_owner
                        bag_owner_status[bag_id] = "owned"
                    else:
                        if evidence.get("state") not in {"temporary_unattended", "unattended"}:
                            evidence["state"] = "temporary_unattended"
                            evidence["state_started_at"] = now
                            print(f"[OWNERSHIP] Temporary unattended started for bag {bag_id} at camera {camera_key}")
                        elif evidence.get("state") == "temporary_unattended":
                            started_at = evidence.get("state_started_at")
                            if started_at is not None and (now - started_at) >= UNATTENDED_TIMEOUT_SECONDS:
                                evidence["state"] = "unattended"
                                evidence["state_started_at"] = started_at
                                print(f"[OWNERSHIP] Unattended timeout expired for bag {bag_id} at camera {camera_key}")
                        bag_owner_state.pop(bag_id, None)
                        owner_map[bag_id] = None
                        bag_owner_status[bag_id] = evidence.get("state", "temporary_unattended")
                else:
                    evidence["state"] = "unknown"
                    evidence["state_started_at"] = None
                    owner_map[bag_id] = None
                    bag_owner_status[bag_id] = "unknown"
            else:
                evidence["missing_streak"] = 0
                if confirmed_owner is not None and confirmed_owner == best_owner:
                    evidence["confirm_streak"] = max(int(evidence.get("confirm_streak", 0)), OWNERSHIP_ASSIGNMENT_REQUIRED_FRAMES)
                    evidence["candidate_owner"] = best_owner
                    evidence["confirmed_owner"] = best_owner
                    evidence["confirmed_owner_person_id"] = person_ids.get(best_owner)
                    evidence["state"] = "owned"
                    evidence["state_started_at"] = None
                    bag_owner_state[bag_id] = best_owner
                    if evidence["confirmed_owner_person_id"] is not None:
                        bag_owner_person_state[bag_id] = evidence["confirmed_owner_person_id"]
                    owner_map[bag_id] = best_owner
                    bag_owner_status[bag_id] = "owned"
                else:
                    candidate_owner = evidence.get("candidate_owner")
                    if candidate_owner == best_owner:
                        evidence["confirm_streak"] = int(evidence.get("confirm_streak", 0)) + 1
                    else:
                        evidence["candidate_owner"] = best_owner
                        evidence["confirm_streak"] = 1

                    if evidence["confirm_streak"] >= OWNERSHIP_ASSIGNMENT_REQUIRED_FRAMES:
                        evidence["confirmed_owner"] = best_owner
                        evidence["confirmed_owner_person_id"] = person_ids.get(best_owner)
                        evidence["state"] = "owned"
                        evidence["state_started_at"] = None
                        bag_owner_state[bag_id] = best_owner
                        if evidence["confirmed_owner_person_id"] is not None:
                            bag_owner_person_state[bag_id] = evidence["confirmed_owner_person_id"]
                        owner_map[bag_id] = best_owner
                        bag_owner_status[bag_id] = "owned"
                    else:
                        evidence["state"] = "unknown"
                        evidence["state_started_at"] = None
                        owner_map[bag_id] = None
                        bag_owner_status[bag_id] = "unknown"

        for stale_bag_id in list(bag_owner_state.keys()):
            if stale_bag_id not in visible_bag_ids:
                del bag_owner_state[stale_bag_id]
        for stale_bag_id in list(bag_owner_person_state.keys()):
            if stale_bag_id not in visible_bag_ids:
                del bag_owner_person_state[stale_bag_id]
        for stale_bag_id in list(bag_owner_evidence.keys()):
            if stale_bag_id not in visible_bag_ids:
                del bag_owner_evidence[stale_bag_id]
        for stale_bag_id in list(bag_owner_status.keys()):
            if stale_bag_id not in visible_bag_ids:
                del bag_owner_status[stale_bag_id]

        if getattr(self, "bag_owner_state", None) is None:
            self.bag_owner_state = {}
        if getattr(self, "bag_owner_person_state", None) is None:
            self.bag_owner_person_state = {}
        if getattr(self, "bag_owner_evidence", None) is None:
            self.bag_owner_evidence = {}
        if getattr(self, "bag_owner_status", None) is None:
            self.bag_owner_status = {}

        self.bag_owner_state[camera_key] = bag_owner_state
        self.bag_owner_person_state[camera_key] = bag_owner_person_state
        self.bag_owner_evidence[camera_key] = bag_owner_evidence
        self.bag_owner_status[camera_key] = bag_owner_status

        return owner_map

    @staticmethod
    def _format_overlay_label(track_id, label_name, status=None):
        """Render a compact overlay label that includes the persistent track ID."""
        if label_name is None:
            base_label = "Object"
        elif str(label_name).lower() == "person":
            base_label = "Person"
        elif str(label_name).lower() in {"bag", "backpack", "suitcase", "baggage"}:
            base_label = "Baggage"
        else:
            base_label = str(label_name).capitalize()

        if track_id is None:
            label = base_label
        else:
            try:
                label = f"ID:{int(track_id):03d} {base_label}"
            except (TypeError, ValueError):
                label = f"ID:{track_id} {base_label}"

        if status and str(status).upper() not in {"NORMAL", ""}:
            label = f"{label} [{str(status).upper()}]"

        return label

    @staticmethod
    def _get_overlay_draw_settings(frame_shape):
        """Return compact display settings that keep labels readable without blocking the scene."""
        height = max(1, int(frame_shape[0]))
        width = max(1, int(frame_shape[1]))
        scale = min(width / 1280.0, height / 720.0)
        font_scale = max(0.28, min(0.5, 0.32 + scale * 0.1))
        line_thickness = max(1, int(round(1 + scale)))
        padding = max(2, int(round(2 + scale * 0.8)))
        return {
            "font_scale": font_scale,
            "line_thickness": line_thickness,
            "padding": padding,
        }

    @staticmethod
    def _get_text_color(background_color):
        """Choose a high-contrast text color for the label background."""
        r, g, b = background_color
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0
        return (0, 0, 0) if luminance > 0.55 else (255, 255, 255)

    @staticmethod
    def _draw_detection_overlay(frame, x1, y1, x2, y2, label, color, draw_settings):
        """Draw a compact, high-contrast detection box and label on the frame."""
        if frame is None:
            return

        thickness = draw_settings["line_thickness"]
        padding = draw_settings["padding"]
        font_scale = draw_settings["font_scale"]
        text_thickness = max(1, int(round(thickness / 2)))

        points = [
            (x1, y1),
            (x2, y1),
            (x2, y2),
            (x1, y2),
        ]
        for idx, point in enumerate(points):
            next_point = points[(idx + 1) % len(points)]
            cv2.line(frame, point, next_point, color, thickness, cv2.LINE_AA)

        lines = str(label).split("\n")
        line_sizes = [cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, font_scale, text_thickness) for line in lines]
        text_width = max(size[0][0] for size in line_sizes)
        line_height = max(size[0][1] for size in line_sizes)
        baseline = max(size[1] for size in line_sizes)
        line_spacing = max(2, padding // 2)
        text_height = line_height * len(lines) + line_spacing * max(0, len(lines) - 1)

        text_color = AIProcessor._get_text_color(color)
        label_x = max(0, int(x1 + max(1, padding // 2)))
        label_y = max(text_height + max(1, padding // 2), int(y1 - max(1, padding // 2)))
        label_x1 = max(0, label_x - max(1, padding // 2))
        label_y1 = max(0, label_y - text_height - max(1, padding // 2))
        label_x2 = min(frame.shape[1], label_x + text_width + max(1, padding // 2))
        label_y2 = min(frame.shape[0], label_y + baseline + max(1, padding // 2) + text_height - line_height)

        cv2.rectangle(frame, (label_x1, label_y1), (label_x2, label_y2), color, -1)
        for idx, line in enumerate(lines):
            line_y = label_y + idx * (line_height + line_spacing)
            cv2.putText(
                frame,
                line,
                (label_x, line_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                font_scale,
                text_color,
                text_thickness,
                cv2.LINE_AA,
            )

    async def process_camera(
        self,
        camera_id,
        rtsp_url,
        db: Session = None,
        reserved: bool = False,
    ):
        """المحرك الشامل: معالجة البث الحي أو الفيديوهات المرفوعة (Section 5 & 13)"""
        camera_id_str = str(camera_id)
        if reserved:
            with self._active_camera_lock:
                owns_camera = (
                    camera_id_str in self._active_cameras
                    and camera_id_str in self._stop_flags
                )
            if not owns_camera:
                return
        elif self.reserve_camera_start(camera_id) != "reserved":
            print(f"⚠️ [{camera_id}] camera already processing, skipping duplicate start")
            return

        local_db = None
        own_db = db is None
        cap = None
        capture_released = False
        consecutive_read_failures = 0
        last_frame_pos = -1
        status_broadcasted = False
        camera_owner_id = None
        last_frame_received_at = None
        try:
            local_db = db if db is not None else SessionLocal()
            if self._camera_stop_requested(camera_id_str):
                return
            self._initialize_camera_runtime_state(camera_id_str)
            await manager.broadcast({
                "event": "camera_status",
                "data": {
                    "camera_id": str(camera_id),
                    "status": "Processing",
                }
            })
            if self._camera_stop_requested(camera_id_str):
                return
            # 1. تحديد نوع المصدر ومعالجته
            source = 0 if str(rtsp_url) == "0" else rtsp_url
            is_file_source = False
            if isinstance(source, str) and not source.isdigit():
                is_file_source = not source.startswith(("rtsp://", "http://", "https://", "rtmp://"))
                if is_file_source and not os.path.isabs(source):
                    backend_root = os.path.abspath(
                        os.path.join(os.path.dirname(__file__), "..", "..")
                    )
                    source = os.path.abspath(os.path.join(backend_root, source))
                    print(f"📌 [{camera_id}] resolved source path={source}")

            with self._active_camera_lock:
                startup_time = self._camera_started_at.get(
                    camera_id_str,
                    time.monotonic(),
                )

            print(
                f"📌 [{camera_id}] source={source!r} type={type(source).__name__} file_source={is_file_source}"
            )
            if is_file_source:
                cap = cv2.VideoCapture(source)
            else:
                cap = cv2.VideoCapture()
                capture_opened = await self._open_live_capture(
                    cap,
                    source,
                    camera_id_str,
                    startup_time + CAMERA_NO_FRAME_GRACE_SECONDS,
                )
                if capture_opened is None:
                    capture_released = True
                    return
                if not capture_opened:
                    print(f"❌ Critical: Could not open camera/video {camera_id}")
                    return
            print(f"📌 [{camera_id}] cap created, isOpened={cap.isOpened()}")

            # 2. تحميل إعدادات المناطق المحظورة (نُحمّلها أولياً ونقوم بتحديثها دورياً داخل الحلقة)
            zones = []
            try:
                zones = local_db.query(RestrictedZone).filter(RestrictedZone.camera_id == camera_id).all()
            except Exception as zone_exc:
                print(f"⚠️ [{camera_id}] failed to load restricted zones: {type(zone_exc).__name__}: {zone_exc}")
                zones = []
                local_db.rollback()
            # helper to compute side of point relative to a line
            def _point_side(a, b, p):
                # cross product (b-a) x (p-a)
                return (b[0]-a[0])*(p[1]-a[1]) - (b[1]-a[1])*(p[0]-a[0])

            # 3. التحقق من الإعدادات
            cam = local_db.query(Camera).filter(Camera.camera_id == camera_id).first()
            camera_owner_id = getattr(cam, "owner_id", None) if cam else None
            try:
                settings_row = (
                    local_db.query(UserSettings)
                    .filter(UserSettings.owner_id == camera_owner_id)
                    .first()
                    if camera_owner_id
                    else None
                )
                camera_settings = self._get_settings_for_owner(camera_owner_id)
                if camera_settings is None and settings_row is not None:
                    settings_snapshot = self._snapshot_camera_settings(settings_row)
                    with self._settings_lock:
                        camera_settings = self._settings_by_owner.setdefault(
                            str(camera_owner_id),
                            settings_snapshot,
                        )
            except Exception as settings_exc:
                print(f"⚠️ [{camera_id}] failed to load settings: {type(settings_exc).__name__}: {settings_exc}")
                camera_settings = None
                local_db.rollback()
                raise RuntimeError(
                    f"Failed to load AI settings for camera {camera_id}"
                ) from settings_exc

            conf_thr = 0.5
            max_objs = 50
            if camera_settings is not None:
                conf_thr = getattr(camera_settings, "detection_confidence", 0.5)
                max_objs = getattr(camera_settings, "max_objects", 50)

            person_conf_thr = self._get_person_confidence_threshold(conf_thr)

            if conf_thr is None:
                conf_thr = 0.5
            if max_objs is None:
                max_objs = 50

            if not cap.isOpened():
                print(f"❌ Critical: Could not open camera/video {camera_id}")
                return

            repo = DetectionRepository(local_db)
            ai_service = AIService(local_db)
            print(f"🛡️ AeroGuard Monitoring Initiated: {camera_id}")

            iteration = 0
            last_valid_frame = 0
            frame_period = _get_source_frame_period(cap, is_file_source)
            next_frame_deadline = time.perf_counter()
            while cap.isOpened():
                camera_settings = self._get_settings_for_owner(
                    camera_owner_id,
                    camera_settings,
                )
                iteration += 1
                if self._camera_stop_requested(camera_id_str):
                    print(f"📌 [{camera_id}] stop signal received")
                    break

                if is_file_source:
                    ret, frame = cap.read()
                else:
                    frame_deadline = (
                        last_frame_received_at
                        if last_frame_received_at is not None
                        else startup_time
                    ) + CAMERA_NO_FRAME_GRACE_SECONDS
                    frame_result = await self._read_live_frame(
                        cap,
                        camera_id_str,
                        frame_deadline,
                    )
                    if frame_result is None:
                        capture_released = True
                        if self._camera_stop_requested(camera_id_str):
                            print(f"📌 [{camera_id}] stop signal received during capture read")
                        else:
                            print(
                                f"⚠️ [{camera_id}] no valid frame received for "
                                f"{CAMERA_NO_FRAME_GRACE_SECONDS:g} seconds"
                            )
                        break
                    ret, frame = frame_result

                frame_is_valid = bool(
                    ret
                    and frame is not None
                    and getattr(frame, "size", 0) > 0
                )
                if not frame_is_valid:
                    if isinstance(source, str) and not source.isdigit():
                        
                        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
                        frame_pos = int(cap.get(cv2.CAP_PROP_POS_FRAMES) or 0)
                        consecutive_read_failures += 1

                        if frame_count > 0 and frame_pos >= frame_count:
                            print(
                                f"✅ [{camera_id}] EOF reached after last_valid_frame={last_valid_frame} "
                                f"iterations={iteration-1} source={source!r} frame_pos={frame_pos} frame_count={frame_count}"
                            )
                            break

                        if (
                            consecutive_read_failures >= 3
                            or (frame_pos == last_frame_pos and frame_pos > 0)
                        ):
                            print(
                                f"⚠️ [{camera_id}] persistent read failure, stopping playback "
                                f"source={source!r} frame_pos={frame_pos} frame_count={frame_count} "
                                f"consecutive_failures={consecutive_read_failures}"
                            )
                            break

                        print(
                            f"⚠️ [{camera_id}] transient file read failure at frame_pos={frame_pos} "
                            f"frame_count={frame_count}, retrying ({consecutive_read_failures})"
                        )
                        await asyncio.sleep(0.1)
                        continue
                    print(f"⚠️ [{camera_id}] camera stream read failed, retrying after sleep")
                    with self._active_camera_lock:
                        latest_frame_at = self._last_frame_received_at.get(camera_id_str)
                    no_frame_since = latest_frame_at if latest_frame_at is not None else startup_time
                    remaining = (
                        no_frame_since
                        + CAMERA_NO_FRAME_GRACE_SECONDS
                        - time.monotonic()
                    )
                    if remaining <= 0:
                        print(
                            f"⚠️ [{camera_id}] no valid frame received for "
                            f"{CAMERA_NO_FRAME_GRACE_SECONDS:g} seconds"
                        )
                        break
                    await asyncio.sleep(min(1.0, remaining))
                    continue

                consecutive_read_failures = 0
                last_frame_received_at = time.monotonic()
                self._record_frame_received(camera_id_str)
                frame_pos = int(cap.get(cv2.CAP_PROP_POS_FRAMES) or 0)
                last_frame_pos = frame_pos

                if not status_broadcasted:
                    await manager.broadcast({
                        "event": "camera_status",
                        "data": {
                            "camera_id": str(camera_id),
                            "status": "Running",
                        }
                    })
                    status_broadcasted = True

                if last_valid_frame == 0:
                    print(f"📌 [{camera_id}] first frame decoded successfully")
                last_valid_frame = iteration

                start_time = time.time()

                # respect frame-skip
                frame_skip = 0
                if camera_settings is not None:
                    frame_skip = getattr(camera_settings, "frame_skip", 0) or 0
                if frame_skip is None:
                    frame_skip = 0
                do_infer = (frame_skip <= 0) or (iteration % (frame_skip + 1) == 0)
                results = None
                model_names = None
                specialist_results = _build_empty_model_result()
                specialist_model_names = {}
                if do_infer:
                    results, model_names = await asyncio.to_thread(
                        self._predict_frame,
                        frame,
                        conf_thr,
                    )
                    try:
                        specialist_results, specialist_model_names = (
                            await asyncio.to_thread(
                                self._predict_fire_smoke_frame,
                                frame,
                                conf_thr,
                            )
                        )
                    except Exception as specialist_exc:
                        logger.error(
                            "[%s] fire/smoke inference failed; continuing with general detections: %s: %s",
                            camera_id,
                            type(specialist_exc).__name__,
                            specialist_exc,
                        )
                else:
                    results = _build_empty_model_result()
                annotated_frame = frame.copy()

                try:
                    detections_for_tracker = self._merge_detections(
                        self._extract_model_detections(
                            results,
                            model_names,
                            GENERAL_DETECTION_LABELS
                            | SPECIALIST_DETECTION_LABELS,
                        )
                        + self._extract_model_detections(
                            specialist_results,
                            specialist_model_names,
                            SPECIALIST_DETECTION_LABELS,
                            self.fire_smoke_class_map,
                        )
                    )
                except Exception as box_exc:
                    print(f"⚠️ [{camera_id}] failed to parse model boxes: {type(box_exc).__name__}: {box_exc}")
                    detections_for_tracker = []

                filtered_detections = []
                for detection in detections_for_tracker:
                    label_name = detection["class_name"]
                    detection_confidence = detection["confidence"]
                    if label_name == "person" and detection_confidence < person_conf_thr:
                        continue
                    filtered_detections.append(detection)
                detections_for_tracker = filtered_detections

                camera_tracker = self.trackers[camera_id_str]
                if do_infer:
                    camera_tracker.update(detections_for_tracker)
                active_tracks = camera_tracker.get_active_tracks()
                active_objs_count = len(active_tracks)
                person_count = sum(1 for t in active_tracks if t.class_name == "person")
                bag_count = sum(1 for t in active_tracks if t.class_name in {"bag", "backpack", "suitcase"})
                vehicle_count = sum(
                    1
                    for t in active_tracks
                    if t.class_name in VEHICLE_DETECTION_LABELS
                )
                alarm_sources = set()

                person_ids = self._assign_person_ids(camera_id, active_tracks, frame)
                bag_owner_map = self._assign_bag_owner(
                    camera_id,
                    [t for t in active_tracks if t.class_name == "person"],
                    [t for t in active_tracks if t.class_name in {"bag", "backpack", "suitcase"}],
                    person_ids,
                )
                ownership_state = self.bag_owner_status.get(str(camera_id), {})

                # Periodically refresh zones from DB so saved annotations are applied to live inference
                try:
                    if iteration % 30 == 0:
                        zones = local_db.query(RestrictedZone).filter(RestrictedZone.camera_id == camera_id).all()
                except Exception as zone_reload_exc:
                    print(f"⚠️ [{camera_id}] failed to reload restricted zones: {type(zone_reload_exc).__name__}: {zone_reload_exc}")
                    local_db.rollback()

                restricted_area_enabled = bool(
                    getattr(camera_settings, "restricted_area_enabled", False)
                )
                has_direction_zone = any(
                    "direction" in (zone.zone_type or "").lower()
                    for zone in zones
                )

                active_alert_keys = set()
                for track in active_tracks:
                    if active_objs_count >= max_objs:
                        print(f"📌 [{camera_id}] track loop break due to max_objs={max_objs}")
                        break
                    obj_id = self._get_track_id(track)
                    label_name = track.class_name
                    conf = track.confidence
                    x1, y1, x2, y2 = track.bbox
                    base_point = (int((x1 + x2) / 2), y2)

                    status = "NORMAL"
                    box_color = self._get_detection_box_color(label_name)
                    display_label = _get_detection_persistence_label(label_name)
                    display_id = person_ids.get(obj_id, 0)
                    bag_state = None
                    if label_name in {"bag", "backpack", "suitcase"}:
                        overlay_owner_id = bag_owner_map.get(obj_id)
                        owner_person_id = self.bag_owner_person_state.get(str(camera_id), {}).get(obj_id)
                        bag_evidence = self.bag_owner_evidence.get(str(camera_id), {}).get(obj_id, {})
                        bag_state = bag_evidence.get("state", ownership_state.get(obj_id, "unknown"))
                        if overlay_owner_id is not None:
                            box_color = (0, 255, 0)
                            owner_label_id = owner_person_id if owner_person_id is not None else overlay_owner_id
                            object_label = f"Owned ID {int(owner_label_id):03d} Bag"
                            display_label = "OWNED_BAG"
                            status = "NORMAL"
                            if bag_state in {"temporary_unattended", "unattended"}:
                                print(f"[OWNERSHIP] Owner returned for bag {obj_id} at camera {camera_id}")
                            ownership_state[obj_id] = "owned"
                        elif bag_state == "temporary_unattended":
                            started_at = bag_evidence.get("state_started_at")
                            remaining = 0
                            if started_at is not None:
                                remaining = max(0, int(UNATTENDED_TIMEOUT_SECONDS - (time.time() - started_at)))
                            box_color = (0, 255, 255)
                            object_label = (
                                f"Owned ID {int(owner_person_id):03d} Bag\nLEFT {remaining}s"
                                if owner_person_id is not None
                                else f"LEFT {remaining}s"
                            )
                            display_label = "TEMP_UNATTENDED"
                            status = "NORMAL"
                            ownership_state[obj_id] = "temporary_unattended"
                        elif bag_state == "unattended":
                            box_color = (0, 0, 255)
                            object_label = (
                                f"Owned ID {int(owner_person_id):03d} Bag\nUNATTENDED"
                                if owner_person_id is not None
                                else "UNATTENDED"
                            )
                            display_label = "UNATTENDED"
                            status = "DANGER"
                            ownership_state[obj_id] = "unattended"
                        else:
                            box_color = self._get_detection_box_color(label_name)
                            object_label = "Bag"
                            display_label = "Baggage"
                            status = "NORMAL"
                            ownership_state[obj_id] = "unknown"
                    else:
                        object_label = self._format_overlay_label(display_id, label_name)

                    camera_history = self.object_history.setdefault(str(camera_id), {})
                    overlay_label = object_label
                    alert_key = None
                    in_restricted = False
                    should_skip_rule_engine = (
                        label_name in {"bag", "backpack", "suitcase"}
                        and bag_state == "temporary_unattended"
                    )
                    if should_skip_rule_engine:
                        pass
                    else:
                        for zone in zones:
                            try:
                                coords = _normalize_zone_coords(
                                    getattr(zone, "polygon_coords", None),
                                    camera_id=camera_id,
                                    annotation_id=getattr(zone, "zone_id", None),
                                    rule_type="zone",
                                )
                                if not coords:
                                    continue
                                ztype = (zone.zone_type or "").lower()

                                # Direction rule (line): detect crossing and check allowed direction
                                if "direction" in ztype:
                                    prev_point = camera_history.get(obj_id)
                                    line_coords = _line_coords_in_frame(coords, annotated_frame.shape)
                                    a = tuple(line_coords[0])
                                    b = tuple(line_coords[-1])
                                    cv2.line(annotated_frame, (int(a[0]), int(a[1])), (int(b[0]), int(b[1])), (200, 200, 200), 1)
                                    if prev_point is not None:
                                        side_prev = _point_side(a, b, prev_point)
                                        side_curr = _point_side(a, b, base_point)
                                        if side_prev * side_curr < 0:
                                            # crossed the direction line this frame
                                            move_vec = (base_point[0] - prev_point[0], base_point[1] - prev_point[1])
                                            dir_vec = (b[0] - a[0], b[1] - a[1])
                                            dot = move_vec[0] * dir_vec[0] + move_vec[1] * dir_vec[1]
                                            # if dot < 0 => moving opposite to defined direction => violation
                                            if dot < 0:
                                                status = "DANGER"
                                                box_color = (0, 0, 255)
                                                display_label = "WRONG DIRECTION"
                                                overlay_label = f"{object_label}\nWRONG DIRECTION"
                                                alert_key = f"{camera_id}_{obj_id}_WRONG_DIR_{getattr(zone, 'zone_id', '')}"
                                                await self._register_persistent_alert(
                                                    ai_service,
                                                    camera_id,
                                                    alert_key,
                                                    display_label,
                                                    "Critical",
                                                    float(conf),
                                                    str(obj_id),
                                                    camera_owner_id,
                                                    {"bbox": [x1, y1, x2, y2]},
                                                    annotated_frame,
                                                    active_alert_keys,
                                                )

                                # Tripwire: any crossing of the defined line triggers one alert per crossing
                                elif "tripwire" in ztype:
                                    prev_point = camera_history.get(obj_id)
                                    line_coords = _line_coords_in_frame(coords, annotated_frame.shape)
                                    a = tuple(line_coords[0])
                                    b = tuple(line_coords[-1])
                                    cv2.line(annotated_frame, (int(a[0]), int(a[1])), (int(b[0]), int(b[1])), (255, 255, 255), 1)
                                    if prev_point is not None:
                                        side_prev = _point_side(a, b, prev_point)
                                        side_curr = _point_side(a, b, base_point)
                                        if side_prev * side_curr < 0:
                                            status = "DANGER"
                                            box_color = (0, 0, 255)
                                            display_label = "TRIPWIRE"
                                            overlay_label = f"{object_label}\nTRIPWIRE CROSSED"
                                            alert_key = f"{camera_id}_{obj_id}_TRIPWIRE_{getattr(zone, 'zone_id', '')}"
                                            await self._register_persistent_alert(
                                                ai_service,
                                                camera_id,
                                                alert_key,
                                                display_label,
                                                "Critical",
                                                float(conf),
                                                str(obj_id),
                                                camera_owner_id,
                                                {"bbox": [x1, y1, x2, y2]},
                                                annotated_frame,
                                                active_alert_keys,
                                            )

                                # Default: restricted polygon area
                                else:
                                    if not restricted_area_enabled:
                                        continue
                                    polygon = np.asarray(coords, dtype=np.float32)
                                    if polygon.size and np.all(polygon >= 0.0) and np.all(polygon <= 1.0):
                                        polygon *= np.array([annotated_frame.shape[1], annotated_frame.shape[0]], dtype=np.float32)
                                    polygon = np.array(polygon, np.int32)
                                    cv2.polylines(annotated_frame, [polygon], True, (255, 255, 255), 1)

                                    if self._bbox_intersects_polygon((x1, y1, x2, y2), polygon):
                                        in_restricted = True
                                        status = "DANGER"
                                        box_color = (0, 0, 255)
                                        display_label = "RESTRICTED AREA"
                                        overlay_label = f"{object_label}\nRESTRICTED AREA"
                                        break
                            except Exception as zone_exc:
                                print(
                                    f"⚠️ [{camera_id}] failed to normalize zone annotation zone={getattr(zone, 'zone_id', None)} rule={getattr(zone, 'zone_type', None)}: {type(zone_exc).__name__}: {zone_exc}"
                                )
                                continue

                    # legacy wrong-direction vertical heuristic (kept for backward compatibility)
                    if (
                        has_direction_zone
                        and obj_id in camera_history
                        and not in_restricted
                    ):
                        prev_point = camera_history[obj_id]
                        prev_y = prev_point[1]
                        # Wrong direction heuristic (vertical movement upward)
                        wrong_enabled = False
                        if camera_settings is not None:
                            wrong_enabled = getattr(camera_settings, "wrong_direction_enabled", False) or False
                        if wrong_enabled and base_point[1] < prev_y - 30:
                            status = "WARNING"
                            box_color = (0, 0, 255)
                            display_label = "WRONG DIRECTION"

                    # Loitering detection: person staying within small radius
                    if label_name == "person":
                        cam_loiter = self.loitering_tracker.setdefault(str(camera_id), {})
                        rec = cam_loiter.get(obj_id)
                        now_ts = time.time()
                        if rec is None:
                            cam_loiter[obj_id] = {"first_seen": now_ts, "last_pos": base_point, "last_move": now_ts}
                        else:
                            last_pos = rec.get("last_pos", base_point)
                            dx = base_point[0] - last_pos[0]
                            dy = base_point[1] - last_pos[1]
                            dist = (dx * dx + dy * dy) ** 0.5
                            if dist > 20:
                                rec["last_move"] = now_ts
                                rec["last_pos"] = base_point
                            else:
                                # stayed roughly in place
                                loiter_enabled = False
                                loiter_seconds = 30
                                if camera_settings is not None:
                                    loiter_enabled = getattr(camera_settings, "loitering_enabled", False) or False
                                    loiter_seconds = getattr(camera_settings, "loitering_seconds", 30) or 30
                                if loiter_enabled and (now_ts - rec.get("last_move", now_ts) >= loiter_seconds):
                                    status = "WARNING"
                                    box_color = (0, 255, 255)
                                    display_label = "LOITERING"

                    camera_history[obj_id] = base_point

                    # Fire / Smoke detections must be classified before persistence
                    # so analytics receives the same label and severity as alerts.
                    should_trigger_fire_smoke = self._is_fire_smoke_enabled(
                        label_name,
                        camera_settings,
                    )
                    if should_trigger_fire_smoke:
                        status = "DANGER"
                        box_color = (0, 0, 255)
                        display_label = label_name.upper()
                        overlay_label = f"{object_label}\n{display_label}"
                        alarm_sources.add(display_label)

                    # Persist detections so analytics has real data even for non-alert objects
                    self._persist_detection(
                        local_db,
                        camera_id,
                        camera_owner_id,
                        display_label,
                        float(conf),
                        obj_id,
                        status,
                    )

                    if status == "DANGER":
                        alarm_sources.add(display_label)

                    # Abandoned bag detection
                    if label_name in {"bag", "backpack", "suitcase"}:
                        cam_bags = self.bag_tracker.setdefault(str(camera_id), {})
                        now_ts = time.time()
                        bag_rec = cam_bags.get(obj_id)
                        # find nearest person
                        nearest_person_dist = None
                        for p in active_tracks:
                            if p.class_name == "person":
                                px1, py1, px2, py2 = p.bbox
                                p_center = (int((px1 + px2) / 2), int((py1 + py2) / 2))
                                dx = p_center[0] - base_point[0]
                                dy = p_center[1] - base_point[1]
                                d = (dx * dx + dy * dy) ** 0.5
                                if nearest_person_dist is None or d < nearest_person_dist:
                                    nearest_person_dist = d
                        if bag_rec is None:
                            cam_bags[obj_id] = {"first_seen": now_ts, "last_near_person": now_ts if (nearest_person_dist is not None and nearest_person_dist < 120) else 0}
                        else:
                            if nearest_person_dist is not None and nearest_person_dist < 120:
                                bag_rec["last_near_person"] = now_ts
                            # evaluate abandoned
                            abandoned_enabled = False
                            abandoned_seconds = 20
                            if camera_settings is not None:
                                abandoned_enabled = getattr(camera_settings, "abandoned_bag_enabled", False) or False
                                abandoned_seconds = getattr(camera_settings, "abandoned_bag_seconds", 20) or 20
                            if abandoned_enabled:
                                first_seen = bag_rec.get("first_seen", now_ts)
                                last_near = bag_rec.get("last_near_person", 0)
                                if (now_ts - first_seen >= abandoned_seconds) and (now_ts - last_near >= abandoned_seconds):
                                    alert_key = f"{camera_id}_{obj_id}_ABANDONED"
                                    await self._register_persistent_alert(
                                        ai_service,
                                        camera_id,
                                        alert_key,
                                        "ABANDONED_BAG",
                                        "High",
                                        float(conf),
                                        str(obj_id),
                                        camera_owner_id,
                                        {"bbox": [x1, y1, x2, y2]},
                                        annotated_frame,
                                        active_alert_keys,
                                    )

                    if status in ["DANGER", "WARNING"]:
                        if overlay_label == object_label:
                            overlay_label = f"{object_label}\n{display_label}"
                        alert_key = alert_key or f"{camera_id}_{obj_id}_{display_label}"
                        if status == "DANGER" and alert_key not in self.alert_persistence:
                            self._register_critical_alert(camera_id)
                        await self._register_persistent_alert(
                            ai_service,
                            camera_id,
                            alert_key,
                            display_label,
                            "Critical" if status == "DANGER" else "High",
                            float(conf),
                            str(obj_id),
                            camera_owner_id,
                            {"bbox": [x1, y1, x2, y2]},
                            annotated_frame,
                            active_alert_keys,
                        )

                    draw_settings = self._get_overlay_draw_settings(annotated_frame.shape)
                    self._draw_detection_overlay(
                        annotated_frame,
                        x1,
                        y1,
                        x2,
                        y2,
                        overlay_label,
                        box_color,
                        draw_settings,
                    )

                    if alert_key is not None:
                        await self._register_persistent_alert(
                            ai_service,
                            camera_id,
                            alert_key,
                            display_label,
                            "Critical" if status == "DANGER" else "High",
                            float(conf),
                            str(obj_id),
                            camera_owner_id,
                            {"bbox": [x1, y1, x2, y2]},
                            annotated_frame,
                            active_alert_keys,
                            capture_screenshot=True,
                        )

                self._reset_inactive_alert_persistence(camera_id, active_alert_keys)

                elapsed = time.time() - start_time
                current_fps = (
                    int(round(1.0 / frame_period))
                    if frame_period is not None
                    else int(1.0 / elapsed) if elapsed > 0 else 30
                )
                critical_alert_count = self._get_active_critical_alert_count(camera_id)
                new_alarm_active = len(alarm_sources) > 0
                camera_key = str(camera_id)
                existing_alarm_active = self._active_alarm_state.get(camera_key, False)
                existing_alarm_sources = self._active_alarm_sources.get(camera_key, [])
                current_alarm_sources = sorted(alarm_sources)

                if (
                    new_alarm_active != existing_alarm_active or
                    current_alarm_sources != existing_alarm_sources
                ):
                    self._active_alarm_state[camera_key] = new_alarm_active
                    self._active_alarm_sources[camera_key] = current_alarm_sources
                    await self._broadcast_alarm_state(
                        camera_id,
                        new_alarm_active,
                        current_alarm_sources,
                        camera_owner_id,
                    )

                await manager.broadcast({
                    "event": "ai_status",
                    "data": {
                        "fps": current_fps,
                        "objects": active_objs_count,
                        "persons": person_count,
                        "bags": bag_count,
                        "cars": vehicle_count,
                        "critical_alerts": critical_alert_count,
                        "camera_id": str(camera_id)
                   }
                })

                self.last_frames[str(camera_id)] = annotated_frame
                if frame_period is not None:
                    next_frame_deadline += frame_period
                    remaining = next_frame_deadline - time.perf_counter()
                    if remaining > 0:
                        await asyncio.sleep(remaining)
                    else:
                        next_frame_deadline = time.perf_counter()
                else:
                    await asyncio.sleep(0.01)
        except Exception as exc:
            print(f"❌ [{camera_id}] unexpected termination: {type(exc).__name__}: {exc}")
        finally:
            if cap is not None and not capture_released:
                try:
                    cap.release()
                    print(f"📌 [{camera_id}] cap released and processing ended")
                except Exception as exc:
                    print(f"⚠️ [{camera_id}] capture release failed: {type(exc).__name__}: {exc}")
            if self._active_alarm_state.get(camera_id_str, False):
                try:
                    await self._broadcast_alarm_state(
                        camera_id,
                        False,
                        [],
                        camera_owner_id,
                    )
                except Exception as exc:
                    print(f"⚠️ [{camera_id}] alarm cleanup broadcast failed: {type(exc).__name__}: {exc}")

            try:
                self._clear_camera_runtime_state(camera_id_str)
            except Exception as exc:
                print(f"⚠️ [{camera_id}] runtime state cleanup failed: {type(exc).__name__}: {exc}")
            with self._active_camera_lock:
                self._stop_flags.pop(camera_id_str, None)
                self._active_cameras.discard(camera_id_str)
                self._starting_cameras.discard(camera_id_str)
                self._camera_started_at.pop(camera_id_str, None)
                self._last_frame_received_at.pop(camera_id_str, None)

            cleanup_db = local_db
            if cleanup_db is None and own_db:
                try:
                    cleanup_db = SessionLocal()
                except Exception as exc:
                    print(f"⚠️ [{camera_id}] cleanup database session unavailable: {type(exc).__name__}: {exc}")
            try:
                if cleanup_db is not None:
                    camera = cleanup_db.query(Camera).filter(
                        Camera.camera_id == camera_id
                    ).first()
                    if camera is not None and camera.status != "Offline":
                        camera.status = "Offline"
                        cleanup_db.commit()
            except Exception as exc:
                print(f"⚠️ [{camera_id}] failed to persist Offline status: {type(exc).__name__}: {exc}")
                if cleanup_db is not None:
                    try:
                        cleanup_db.rollback()
                    except Exception as rollback_exc:
                        print(f"⚠️ [{camera_id}] database rollback failed: {type(rollback_exc).__name__}: {rollback_exc}")
            finally:
                if own_db and cleanup_db is not None:
                    try:
                        cleanup_db.close()
                    except Exception as close_exc:
                        print(f"⚠️ [{camera_id}] database close failed: {type(close_exc).__name__}: {close_exc}")

            try:
                await manager.broadcast({
                    "event": "camera_status",
                    "data": {
                        "camera_id": str(camera_id),
                        "status": "Offline",
                    }
                })
            except Exception as exc:
                print(f"⚠️ [{camera_id}] terminal status broadcast failed: {type(exc).__name__}: {exc}")

    def stop_camera(self, camera_id):
        camera_key = str(camera_id)
        with self._active_camera_lock:
            if (
                camera_key in self._active_cameras
                or camera_key in self._starting_cameras
            ):
                self._stop_flags[camera_key] = True

    def stop_all_other_cameras(self, keep_camera_id):
        current_key = str(keep_camera_id)
        with self._active_camera_lock:
            camera_ids = [camera_id for camera_id in list(self._active_cameras) if str(camera_id) != current_key]

        for camera_id in camera_ids:
            self.stop_camera(camera_id)


# تصدير نسخة المحرك الموحدة

try:
    ai_engine = AIProcessor(model_path="models/yolov8n.pt")
except Exception as exc:
    # Allow the application to start even if the AI model cannot be loaded
    # (e.g., during CI, dev environments, or when offline). The service
    # should check `ai_engine` is not None before using it.
    print(f"⚠️ AIProcessor initialization failed: {type(exc).__name__}: {exc}")
    ai_engine = None