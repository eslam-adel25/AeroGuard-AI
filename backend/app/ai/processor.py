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
        self._stop_flags = {}
        self._active_cameras = set()
        self._active_camera_lock = threading.Lock()
        
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
        try:
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

            # 2. تحميل إعدادات المناطق المحظورة
            zones = []
            try:
                zones = local_db.query(RestrictedZone).filter(RestrictedZone.camera_id == camera_id).all()
            except Exception as zone_exc:
                print(f"⚠️ [{camera_id}] failed to load restricted zones: {type(zone_exc).__name__}: {zone_exc}")
                zones = []
                local_db.rollback()

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
                    if label_name not in ["person", "bag", "suitcase", "backpack", "car", "truck", "bus", "vehicle", "fire", "smoke"]:
                        continue
                    detections_for_tracker.append({
                        "bbox": [int(x1), int(y1), int(x2), int(y2)],
                        "class_name": label_name,
                        "confidence": float(conf),
                    })

                tracks = self.tracker.update(detections_for_tracker)
                active_tracks = self.tracker.get_active_tracks()
                active_objs_count = len(active_tracks)
                person_count = sum(1 for t in active_tracks if t.class_name == "person")
                bag_count = sum(1 for t in active_tracks if t.class_name in {"bag", "backpack", "suitcase"})
                vehicle_count = sum(1 for t in active_tracks if t.class_name in {"car", "truck", "bus", "vehicle"})

                for track in active_tracks:
                    if active_objs_count >= max_objs:
                        print(f"📌 [{camera_id}] track loop break due to max_objs={max_objs}")
                        break
                    obj_id = track.track_id
                    label_name = track.class_name
                    conf = track.confidence
                    x1, y1, x2, y2 = track.bbox
                    base_point = (int((x1 + x2) / 2), y2)

                    status = "NORMAL"
                    box_color = (0, 255, 0)
                    display_label = "Person" if label_name == "person" else "Baggage"

                    in_restricted = False
                    for zone in zones:
                        polygon = np.array(zone.polygon_coords, np.int32)
                        cv2.polylines(annotated_frame, [polygon], True, (255, 255, 255), 1)
                        if cv2.pointPolygonTest(polygon, base_point, False) >= 0:
                            in_restricted = True
                            status = "DANGER"
                            box_color = (0, 0, 255)
                            display_label = f"RESTRICTED AREA"
                            break

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

                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), box_color, 2)
                    label_size, _ = cv2.getTextSize(f"{display_label}", cv2.FONT_HERSHEY_DUPLEX, 0.5, 1)
                    cv2.rectangle(annotated_frame, (x1, y1 - 25), (x1 + label_size[0] + 10, y1), box_color, -1)
                    cv2.putText(annotated_frame, f"{display_label}", (x1 + 5, y1 - 8),
                                cv2.FONT_HERSHEY_DUPLEX, 0.5, (255, 255, 255), 1)

                    # Fire / Smoke immediate critical events
                    # Check if fire/smoke detection is enabled
                    fire_enabled = getattr(self.active_settings, "fire_detection_enabled", False) or False
                    smoke_enabled = getattr(self.active_settings, "smoke_detection_enabled", False) or False
                    
                    should_trigger_fire_smoke = (
                        (label_name == "fire" and fire_enabled) or
                        (label_name == "smoke" and smoke_enabled)
                    )
                    
                    if should_trigger_fire_smoke:
                        status = "DANGER"
                        box_color = (0, 0, 255)
                        display_label = label_name.upper()

                    if status in ["DANGER", "WARNING"]:
                        alert_key = f"{camera_id}_{obj_id}_{status}"
                        if time.time() - self.last_alert_time.get(alert_key, 0) > 5:
                            # attach owner based on camera
                            cam = local_db.query(Camera).filter(Camera.camera_id == camera_id).first()
                            owner_id = getattr(cam, 'owner_id', None) if cam else None
                            new_det = Detection(
                                camera_id=camera_id,
                                owner_id=owner_id,
                                detection_type=display_label,
                                confidence=float(conf),
                                priority="Critical" if status == "DANGER" else "High",
                                is_violation=True,
                                violation_type=status
                            )
                            repo.save_detection(new_det)
                            # also register AIEvent and broadcast
                            try:
                                # capture a quick JPEG of the annotated frame
                                _, jpg = cv2.imencode('.jpg', annotated_frame)
                                img_bytes = jpg.tobytes() if jpg is not None else None
                            except Exception:
                                img_bytes = None

                            ai_service.register_event(
                                camera_id=camera_id,
                                detection_type=display_label,
                                severity="Critical" if status == "DANGER" else "High",
                                confidence=float(conf),
                                track_id=str(obj_id),
                                user_id=owner_id,
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

                elapsed = time.time() - start_time
                current_fps = int(1.0 / elapsed) if elapsed > 0 else 30

                await manager.broadcast({
                    "event": "ai_status",
                    "data": {
                        "fps": current_fps,
                        "objects": active_objs_count,
                        "persons": person_count,
                        "bags": bag_count,
                        "cars": vehicle_count,
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
            self.last_frames.pop(str(camera_id), None)
            self._stop_flags.pop(camera_id_str, None)
            with self._active_camera_lock:
                self._active_cameras.discard(camera_id_str)
            if own_db:
                local_db.close()

    def stop_camera(self, camera_id):
        self._stop_flags[str(camera_id)] = True


# تصدير نسخة المحرك الموحدة

try:
    ai_engine = AIProcessor(model_path="models/yolov8n.pt")
except Exception as exc:
    # Allow the application to start even if the AI model cannot be loaded
    # (e.g., during CI, dev environments, or when offline). The service
    # should check `ai_engine` is not None before using it.
    print(f"⚠️ AIProcessor initialization failed: {type(exc).__name__}: {exc}")
    ai_engine = None