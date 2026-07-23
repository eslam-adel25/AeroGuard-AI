import cv2
import asyncio
import time
import os
import threading
from pathlib import Path
import numpy as np
import torch
from ultralytics import YOLO
from ultralytics.nn import tasks as ultralytics_tasks
from sqlalchemy.orm import Session
from ..database.session import SessionLocal
from ..models.models import Detection, Camera, RestrictedZone, SystemSettings
from ..repositories.detection_repository import DetectionRepository
from ..services.decision_engine import DecisionEngine
from ..websocket.manager import manager
from .tracker import TrackerManager
from ..services.ai_service import AIService


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


class AIProcessor:
    def __init__(self, model_path: str):
        # تحميل الموديل لمرة واحدة عند التشغيل (صفحة 163)
        self.model_path = self._resolve_model_path(model_path)
        self._patch_ultralytics_weights_only()
        self.model = YOLO(self.model_path)
        self.decision_engine = DecisionEngine()
        # Tracker (stable facade). Default uses IoU fallback; swap later with ByteTrack/DeepSORT adapter.
        self.tracker = TrackerManager()
        self.tracker.initialize()
        
        # مخازن الذاكرة الحية
        self.last_frames = {}
        self.last_alert_time = {}
        self.object_history = {}
        self.loitering_tracker = {}  # camera_id -> {track_id: {first_seen, last_pos, last_move_time}}
        self.bag_tracker = {}  # camera_id -> {track_id: {first_seen, last_near_person_time}}
        self.crowd_cooldown = {}  # camera_id -> last_alert_time
        self.display_id_state = {}  # camera_id -> {internal_track_id: display_id}
        self.bag_owner_state = {}  # camera_id -> {bag_internal_id: owner_internal_id}
        self.active_critical_alerts = {}  # camera_id -> [alert_timestamps]
        self._detection_persist_cooldown = {}  # key -> last persisted timestamp
        self._stop_flags = {}
        self._active_cameras = set()
        self._active_camera_lock = threading.Lock()
        self._active_alarm_state = {}  # camera_id -> bool
        self._active_alarm_sources = {}  # camera_id -> list[str]
        
        # كائن الإعدادات النشط في الذاكرة لسرعة الوصول
        self.active_settings = None

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

    async def _broadcast_alarm_state(self, camera_id, active, sources=None):
        camera_key = str(camera_id)
        try:
            await manager.broadcast({
                "event": "alarm_state",
                "data": {
                    "camera_id": str(camera_id),
                    "active": bool(active),
                    "sources": sorted(sources) if sources else [],
                },
            })
        except Exception:
            pass

    def _register_critical_alert(self, camera_id) -> None:
        camera_key = str(camera_id)
        alerts = self.active_critical_alerts.setdefault(camera_key, [])
        alerts.append(time.time())
        now = time.time()
        self.active_critical_alerts[camera_key] = [ts for ts in alerts if now - ts < 5]

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

    def update_config(self, settings_model: SystemSettings):
        """تحديث إعدادات المحرك فور ضغط زر Save في صفحة Settings (Section 2)"""
        self.active_settings = settings_model
        print(f"⚙️ AI Engine updated with new settings: Conf={settings_model.detection_confidence}")
        # adjust model device if GPU flag changed
        try:
            use_gpu = getattr(settings_model, "gpu_enabled", False)
            dev = "cuda" if use_gpu else "cpu"
            # recreate model on requested device
            self.model = YOLO(self.model_path, device=dev)
            print(f"⚙️ AI Engine model reloaded on device={dev}")
        except Exception:
            # ignore if device change not supported in environment
            pass

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

    def _assign_bag_owner(self, camera_id, person_tracks, bag_tracks):
        """Assign a stable owner ID to bags for overlay display without changing tracker internals."""
        camera_key = str(camera_id)
        bag_owner_state = self.bag_owner_state.setdefault(camera_key, {})

        person_candidates = []
        for track in person_tracks:
            bbox = getattr(track, "bbox", None)
            if bbox is None or len(bbox) != 4:
                continue
            person_candidates.append(track)

        owner_map = {}
        for bag_track in bag_tracks:
            bag_id = getattr(bag_track, "track_id", None)
            if bag_id is None:
                continue

            current_owner = bag_owner_state.get(bag_id)
            if current_owner is not None:
                owner_map[bag_id] = current_owner
                continue

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
                if distance > 220:
                    continue
                score = max(0.0, 220.0 - distance)
                if best_score is None or score > best_score:
                    best_score = score
                    best_owner = getattr(person_track, "track_id", None)

            if best_owner is None:
                owner_map[bag_id] = current_owner
            else:
                owner_map[bag_id] = best_owner
                bag_owner_state[bag_id] = best_owner

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

    async def process_camera(self, camera_id, rtsp_url, db: Session = None):
        """المحرك الشامل: معالجة البث الحي أو الفيديوهات المرفوعة (Section 5 & 13)"""
        local_db = db if db is not None else SessionLocal()
        own_db = db is None
        cap = None

        camera_id_str = str(camera_id)
        with self._active_camera_lock:
            if camera_id_str in self._active_cameras:
                print(f"⚠️ [{camera_id}] camera already processing, skipping duplicate start")
                return
            self._active_cameras.add(camera_id_str)

        self._stop_flags[camera_id_str] = False
        consecutive_read_failures = 0
        last_frame_pos = -1
        status_broadcasted = False
        try:
            await manager.broadcast({
                "event": "camera_status",
                "data": {
                    "camera_id": str(camera_id),
                    "status": "Processing",
                }
            })
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

            print(
                f"📌 [{camera_id}] source={source!r} type={type(source).__name__} file_source={is_file_source}"
            )
            cap = cv2.VideoCapture(source, cv2.CAP_DSHOW) if source == 0 else cv2.VideoCapture(source)
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
            try:
                if not self.active_settings:
                    self.active_settings = local_db.query(SystemSettings).first()
            except Exception as settings_exc:
                print(f"⚠️ [{camera_id}] failed to load settings: {type(settings_exc).__name__}: {settings_exc}")
                self.active_settings = None
                local_db.rollback()

            conf_thr = 0.5
            max_objs = 50
            if self.active_settings is not None:
                conf_thr = getattr(self.active_settings, "detection_confidence", 0.5)
                max_objs = getattr(self.active_settings, "max_objects", 50)

            person_conf_thr = self._get_person_confidence_threshold(conf_thr)

            if conf_thr is None:
                conf_thr = 0.5
            if max_objs is None:
                max_objs = 50

            if not cap.isOpened():
                print(f"❌ Critical: Could not open camera/video {camera_id}")
                await manager.broadcast({
                    "event": "camera_status",
                    "data": {
                        "camera_id": str(camera_id),
                        "status": "Offline",
                    }
                })
                return

            repo = DetectionRepository(local_db)
            ai_service = AIService(local_db)
            print(f"🛡️ AeroGuard Monitoring Initiated: {camera_id}")

            iteration = 0
            last_valid_frame = 0
            while cap.isOpened():
                iteration += 1
                ret, frame = cap.read()
                print(
                    f"📌 [{camera_id}] loop={iteration} ret={ret} "
                    f"frame_type={type(frame).__name__} frame_shape={None if frame is None else getattr(frame, 'shape', None)}"
                )
                if self._stop_flags.get(camera_id_str):
                    print(f"📌 [{camera_id}] stop signal received")
                    break

                if not ret:
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
                    await asyncio.sleep(1)
                    continue

                consecutive_read_failures = 0
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
                if self.active_settings is not None:
                    frame_skip = getattr(self.active_settings, "frame_skip", 0) or 0
                if frame_skip is None:
                    frame_skip = 0
                do_infer = (frame_skip <= 0) or (iteration % (frame_skip + 1) == 0)
                results = None
                if do_infer:
                    results = await asyncio.to_thread(self.model.predict, frame, conf=conf_thr, verbose=False)
                else:
                    # create empty results mimic
                    class Empty:
                        boxes = type("B", (), {"xyxy": [], "cls": [], "conf": []})
                    results = [type("R", (), {"boxes": Empty.boxes})()]
                annotated_frame = frame.copy()

                detections_for_tracker = []
                try:
                    result = results[0] if results else None
                    boxes_obj = getattr(result, "boxes", None) if result is not None else None
                    if boxes_obj is not None and hasattr(boxes_obj, "xyxy") and hasattr(boxes_obj, "cls") and hasattr(boxes_obj, "conf"):
                        if len(boxes_obj) > 0:
                            boxes = boxes_obj.xyxy.cpu().numpy()
                            labels = boxes_obj.cls.cpu().numpy().astype(int)
                            confs = boxes_obj.conf.cpu().numpy()
                        else:
                            boxes = []
                            labels = []
                            confs = []
                    else:
                        boxes = []
                        labels = []
                        confs = []
                except Exception as box_exc:
                    print(f"⚠️ [{camera_id}] failed to parse model boxes: {type(box_exc).__name__}: {box_exc}")
                    boxes = []
                    labels = []
                    confs = []

                for box, cls_idx, conf in zip(boxes, labels, confs):
                    x1, y1, x2, y2 = box.astype(int)
                    label_name = self.model.names[int(cls_idx)].lower()
                    if label_name not in ["person", "bag", "suitcase", "backpack", "car", "truck", "bus", "vehicle", "fire", "smoke", "flame"]:
                        continue
                    detection_confidence = float(conf)
                    if label_name == "person" and detection_confidence < person_conf_thr:
                        continue
                    detections_for_tracker.append({
                        "bbox": [int(x1), int(y1), int(x2), int(y2)],
                        "class_name": label_name,
                        "confidence": detection_confidence,
                    })

                tracks = self.tracker.update(detections_for_tracker)
                active_tracks = self.tracker.get_active_tracks()
                active_objs_count = len(active_tracks)
                person_count = sum(1 for t in active_tracks if t.class_name == "person")
                bag_count = sum(1 for t in active_tracks if t.class_name in {"bag", "backpack", "suitcase"})
                vehicle_count = sum(1 for t in active_tracks if t.class_name in {"car", "truck", "bus", "vehicle"})
                alarm_sources = set()

                display_ids = self._assign_display_ids(camera_id, active_tracks)
                bag_owner_map = self._assign_bag_owner(camera_id, [t for t in active_tracks if t.class_name == "person"], [t for t in active_tracks if t.class_name in {"bag", "backpack", "suitcase"}])

                # Periodically refresh zones from DB so saved annotations are applied to live inference
                try:
                    if iteration % 30 == 0:
                        zones = local_db.query(RestrictedZone).filter(RestrictedZone.camera_id == camera_id).all()
                except Exception as zone_reload_exc:
                    print(f"⚠️ [{camera_id}] failed to reload restricted zones: {type(zone_reload_exc).__name__}: {zone_reload_exc}")
                    local_db.rollback()

                cam = local_db.query(Camera).filter(Camera.camera_id == camera_id).first()
                camera_owner_id = getattr(cam, 'owner_id', None) if cam else None

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
                    display_label = "Person" if label_name == "person" else "Baggage"
                    display_id = display_ids.get(obj_id, 0)
                    if label_name in {"bag", "backpack", "suitcase"}:
                        overlay_owner_id = bag_owner_map.get(obj_id)
                        object_label = f"Owner:{overlay_owner_id:03d} Bag" if overlay_owner_id is not None else "Bag"
                    else:
                        object_label = self._format_overlay_label(display_id, label_name)

                    overlay_label = object_label
                    in_restricted = False
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
                                prev_point = self.object_history.get(obj_id)
                                a = tuple(coords[0])
                                b = tuple(coords[-1])
                                cv2.line(annotated_frame, (int(a[0]), int(a[1])), (int(b[0]), int(b[1])), (200, 200, 200), 1)
                                if prev_point is not None:
                                    side_prev = _point_side(a, b, prev_point)
                                    side_curr = _point_side(a, b, base_point)
                                    ###############################
                                    print("=" * 80)
                                    print("[TRIPWIRE]")
                                    print("TRACK:", obj_id)
                                    print("PREV:", prev_point)
                                    print("CURR:", base_point)
                                    print("SIDE PREV:", side_prev)
                                    print("SIDE CURR:", side_curr)
                                    print("=" * 80)
                                    ##########################
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
                                            if time.time() - self.last_alert_time.get(alert_key, 0) > 5:
                                                try:
                                                    _, jpg = cv2.imencode('.jpg', annotated_frame)
                                                    img_bytes = jpg.tobytes() if jpg is not None else None
                                                except Exception:
                                                    img_bytes = None
                                                ai_service.register_event(
                                                    camera_id=camera_id,
                                                    detection_type=display_label,
                                                    severity="Critical",
                                                    confidence=float(conf),
                                                    track_id=str(obj_id),
                                                    user_id=None,
                                                    metadata={"bbox": [x1, y1, x2, y2]},
                                                    screenshot_bytes=img_bytes,
                                                )
                                                await manager.broadcast({
                                                    "event": "new_alert",
                                                    "data": {"type": display_label, "priority": "Critical", "camera_id": str(camera_id)}
                                                })
                                                self.last_alert_time[alert_key] = time.time()

                            # Tripwire: any crossing of the defined line triggers one alert per crossing
                            elif "tripwire" in ztype:
                                prev_point = self.object_history.get(obj_id)
                                a = tuple(coords[0])
                                b = tuple(coords[-1])
                                cv2.line(annotated_frame, (int(a[0]), int(a[1])), (int(b[0]), int(b[1])), (255, 255, 255), 1)
                                if prev_point is not None:
                                    side_prev = _point_side(a, b, prev_point)
                                    side_curr = _point_side(a, b, base_point)
                                    ###################
                                    print("=" * 80)
                                    print("[DIRECTION]")
                                    print("TRACK:", obj_id)
                                    print("PREV:", prev_point)
                                    print("CURR:", base_point)
                                    print("SIDE PREV:", side_prev)
                                    print("SIDE CURR:", side_curr)
                                    print("=" * 80)
                                    #################
                                    if side_prev * side_curr < 0:
                                        status = "DANGER"
                                        box_color = (0, 0, 255)
                                        display_label = "TRIPWIRE"
                                        overlay_label = f"{object_label}\nTRIPWIRE CROSSED"
                                        alert_key = f"{camera_id}_{obj_id}_TRIPWIRE_{getattr(zone, 'zone_id', '')}"
                                        if time.time() - self.last_alert_time.get(alert_key, 0) > 5:
                                            try:
                                                _, jpg = cv2.imencode('.jpg', annotated_frame)
                                                img_bytes = jpg.tobytes() if jpg is not None else None
                                            except Exception:
                                                img_bytes = None
                                            ai_service.register_event(
                                                camera_id=camera_id,
                                                detection_type=display_label,
                                                severity="Critical",
                                                confidence=float(conf),
                                                track_id=str(obj_id),
                                                user_id=None,
                                                metadata={"bbox": [x1, y1, x2, y2]},
                                                screenshot_bytes=img_bytes,
                                            )
                                            await manager.broadcast({
                                                "event": "new_alert",
                                                "data": {"type": display_label, "priority": "Critical", "camera_id": str(camera_id)}
                                            })
                                            self.last_alert_time[alert_key] = time.time()

                            # Default: restricted polygon area
                            else:
                                polygon = np.asarray(coords, dtype=np.float32)
                                if polygon.size and np.all(polygon >= 0.0) and np.all(polygon <= 1.0):
                                    polygon *= np.array([annotated_frame.shape[1], annotated_frame.shape[0]], dtype=np.float32)
                                polygon = np.array(polygon, np.int32)
                                print("POLYGON:", polygon)#####################
                                cv2.polylines(annotated_frame, [polygon], True, (255, 255, 255), 1)
                                #############################
                                print("=" * 80)
                                print("TRACK:", obj_id)
                                print("ZONE TYPE:", ztype)
                                print("ZONE COORDS:", coords)
                                print("BASE POINT:", base_point)
                                print("POLYGON TEST:", cv2.pointPolygonTest(polygon, base_point, False))
                                print("=" * 80)
                               
                                ##############################
                                if cv2.pointPolygonTest(polygon, base_point, False) >= 0:
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
                    if obj_id in self.object_history and not in_restricted:
                        prev_point = self.object_history[obj_id]
                        prev_y = prev_point[1]
                        # Wrong direction heuristic (vertical movement upward)
                        wrong_enabled = False
                        if self.active_settings is not None:
                            wrong_enabled = getattr(self.active_settings, "wrong_direction_enabled", False) or False
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
                                if self.active_settings is not None:
                                    loiter_enabled = getattr(self.active_settings, "loitering_enabled", False) or False
                                    loiter_seconds = getattr(self.active_settings, "loitering_seconds", 30) or 30
                                if loiter_enabled and (now_ts - rec.get("last_move", now_ts) >= loiter_seconds):
                                    status = "DANGER"
                                    box_color = (0, 0, 255)
                                    display_label = "LOITERING"
                                    alert_key = f"{camera_id}_{obj_id}_LOITERING"
                                    if time.time() - self.last_alert_time.get(alert_key, 0) > 5:
                                        # register loitering event
                                        try:
                                            _, jpg = cv2.imencode('.jpg', annotated_frame)
                                            img_bytes = jpg.tobytes() if jpg is not None else None
                                        except Exception:
                                            img_bytes = None
                                        ai_service.register_event(
                                            camera_id=camera_id,
                                            detection_type="LOITERING",
                                            severity="High",
                                            confidence=float(conf),
                                            track_id=str(obj_id),
                                            user_id=None,
                                            metadata={"bbox": [x1, y1, x2, y2]},
                                            screenshot_bytes=img_bytes,
                                        )
                                        await manager.broadcast({
                                            "event": "new_alert",
                                            "data": {"type": display_label, "priority": "High", "camera_id": str(camera_id)}
                                        })
                                        self.last_alert_time[alert_key] = time.time()

                    self.object_history[obj_id] = base_point

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
                            if self.active_settings is not None:
                                abandoned_enabled = getattr(self.active_settings, "abandoned_bag_enabled", False) or False
                                abandoned_seconds = getattr(self.active_settings, "abandoned_bag_seconds", 20) or 20
                            if abandoned_enabled:
                                first_seen = bag_rec.get("first_seen", now_ts)
                                last_near = bag_rec.get("last_near_person", 0)
                                if (now_ts - first_seen >= abandoned_seconds) and (now_ts - last_near >= abandoned_seconds):
                                    alert_key = f"{camera_id}_{obj_id}_ABANDONED"
                                    if time.time() - self.last_alert_time.get(alert_key, 0) > 5:
                                        try:
                                            _, jpg = cv2.imencode('.jpg', annotated_frame)
                                            img_bytes = jpg.tobytes() if jpg is not None else None
                                        except Exception:
                                            img_bytes = None
                                        ai_service.register_event(
                                            camera_id=camera_id,
                                            detection_type="ABANDONED_BAG",
                                            severity="High",
                                            confidence=float(conf),
                                            track_id=str(obj_id),
                                            user_id=None,
                                            metadata={"bbox": [x1, y1, x2, y2]},
                                            screenshot_bytes=img_bytes,
                                        )
                                        await manager.broadcast({
                                            "event": "new_alert",
                                            "data": {"type": "ABANDONED_BAG", "priority": "High", "camera_id": str(camera_id)}
                                        })
                                        self.last_alert_time[alert_key] = time.time()

                    # Fire / Smoke immediate critical events
                    # Check if fire/smoke detection is enabled
                    fire_enabled = getattr(self.active_settings, "fire_detection_enabled", False) or False
                    smoke_enabled = getattr(self.active_settings, "smoke_detection_enabled", False) or False
                    
                    should_trigger_fire_smoke = (
                        (label_name == "fire" and fire_enabled) or
                        (label_name == "smoke" and smoke_enabled)
                    )
                    
                    flame_enabled = getattr(self.active_settings, "fire_detection_enabled", False) or False
                    should_trigger_fire_smoke = (
                        (label_name == "fire" and fire_enabled) or
                        (label_name == "smoke" and smoke_enabled) or
                        (label_name == "flame" and flame_enabled)
                    )

                    if should_trigger_fire_smoke:
                        status = "DANGER"
                        box_color = (0, 0, 255)
                        display_label = label_name.upper()
                        overlay_label = f"{object_label}\n{display_label}"
                        alarm_sources.add(display_label)

                    if status in ["DANGER", "WARNING"]:
                        if overlay_label == object_label:
                            overlay_label = f"{object_label}\n{display_label}"
                        alert_key = f"{camera_id}_{obj_id}_{status}"
                        if time.time() - self.last_alert_time.get(alert_key, 0) > 5:
                            # also register AIEvent and broadcast
                            try:
                                # capture a quick JPEG of the annotated frame
                                _, jpg = cv2.imencode('.jpg', annotated_frame)
                                img_bytes = jpg.tobytes() if jpg is not None else None
                            except Exception:
                                img_bytes = None

                            self._register_critical_alert(camera_id)
                            ai_service.register_event(
                                camera_id=camera_id,
                                detection_type=display_label,
                                severity="Critical" if status == "DANGER" else "High",
                                confidence=float(conf),
                                track_id=str(obj_id),
                                user_id=camera_owner_id,
                                metadata={"bbox": [x1, y1, x2, y2]},
                                screenshot_bytes=img_bytes,
                            )

                            await manager.broadcast({
                                "event": "new_alert",
                                "data": {
                                    "type": display_label,
                                    "priority": "Critical" if status == "DANGER" else "High",
                                    "camera_id": str(camera_id)
                                }
                            })
                            self.last_alert_time[alert_key] = time.time()

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

                elapsed = time.time() - start_time
                current_fps = int(1.0 / elapsed) if elapsed > 0 else 30
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
                await asyncio.sleep(0.01)
        except Exception as exc:
            print(f"❌ [{camera_id}] unexpected termination: {type(exc).__name__}: {exc}")
        finally:
            if cap is not None:
                cap.release()
                print(f"📌 [{camera_id}] cap released and processing ended")
            await manager.broadcast({
                "event": "camera_status",
                "data": {
                    "camera_id": str(camera_id),
                    "status": "Offline",
                }
            })
            self.last_frames.pop(str(camera_id), None)
            self._stop_flags.pop(camera_id_str, None)
            with self._active_camera_lock:
                self._active_cameras.discard(camera_id_str)
            if own_db:
                local_db.close()

    def stop_camera(self, camera_id):
        self._stop_flags[str(camera_id)] = True

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