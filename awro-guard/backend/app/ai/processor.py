import cv2
import asyncio
import time
import os
import numpy as np
from ultralytics import YOLO
from sqlalchemy.orm import Session
from ..database.session import SessionLocal
from ..models.models import Detection, Camera, RestrictedZone, SystemSettings
from ..repositories.detection_repository import DetectionRepository
from ..services.decision_engine import DecisionEngine
from ..websocket.manager import manager
from .tracker import TrackerManager

class AIProcessor:
    def __init__(self, model_path: str):
        # تحميل الموديل لمرة واحدة عند التشغيل (صفحة 163)
        self.model = YOLO(model_path)
        self.decision_engine = DecisionEngine()
        # Tracker (stable facade). Default uses IoU fallback; swap later with ByteTrack/DeepSORT adapter.
        self.tracker = TrackerManager()
        self.tracker.initialize()
        
        # مخازن الذاكرة الحية
        self.last_frames = {} 
        self.last_alert_time = {} 
        self.object_history = {} 
        
        # كائن الإعدادات النشط في الذاكرة لسرعة الوصول
        self.active_settings = None

    def update_config(self, settings_model: SystemSettings):
        """تحديث إعدادات المحرك فور ضغط زر Save في صفحة Settings (Section 2)"""
        self.active_settings = settings_model
        print(f"⚙️ AI Engine updated with new settings: Conf={settings_model.detection_confidence}")

    def get_latest_frame(self, camera_id):
        return self.last_frames.get(str(camera_id))

    async def process_camera(self, camera_id, rtsp_url, db: Session = None):
        """المحرك الشامل: معالجة البث الحي أو الفيديوهات المرفوعة (Section 5 & 13)"""
        local_db = db if db is not None else SessionLocal()
        own_db = db is None
        cap = None

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

            print(f"📌 [{camera_id}] source={source!r} type={type(source).__name__} file_source={is_file_source}")
            cap = cv2.VideoCapture(source, cv2.CAP_DSHOW) if source == 0 else cv2.VideoCapture(source)
            print(f"📌 [{camera_id}] cap created, isOpened={cap.isOpened()}")

            # 2. تحميل إعدادات المناطق المحظورة
            zones = local_db.query(RestrictedZone).filter(RestrictedZone.camera_id == camera_id).all()

            # 3. التحقق من الإعدادات
            if not self.active_settings:
                self.active_settings = local_db.query(SystemSettings).first()

            conf_thr = (
                self.active_settings.detection_confidence
                if self.active_settings
                else 0.5
            )

            max_objs = (
                getattr(self.active_settings, "max_objects", 50)
                if self.active_settings
                else 50
            )

            if not cap.isOpened():
                print(f"❌ Critical: Could not open camera/video {camera_id}")
                return

            repo = DetectionRepository(local_db)
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
                if not ret:
                    if isinstance(source, str) and not source.isdigit():
                        print(
                            f"✅ [{camera_id}] EOF reached after last_valid_frame={last_valid_frame} "
                            f"iterations={iteration-1} source={source!r}"
                        )
                        break
                    print(f"⚠️ [{camera_id}] camera stream read failed, retrying after sleep")
                    await asyncio.sleep(1)
                    continue

                if last_valid_frame == 0:
                    print(f"📌 [{camera_id}] first frame decoded successfully")
                last_valid_frame = iteration

                start_time = time.time()

                results = await asyncio.to_thread(self.model.predict, frame, conf=conf_thr, verbose=False)
                annotated_frame = frame.copy()

                detections_for_tracker = []
                boxes = results[0].boxes.xyxy.cpu().numpy() if len(results[0].boxes) > 0 else []
                labels = results[0].boxes.cls.cpu().numpy().astype(int) if len(results[0].boxes) > 0 else []
                confs = results[0].boxes.conf.cpu().numpy() if len(results[0].boxes) > 0 else []

                for box, cls_idx, conf in zip(boxes, labels, confs):
                    x1, y1, x2, y2 = box.astype(int)
                    label_name = self.model.names[int(cls_idx)].lower()
                    if label_name not in ["person", "bag", "suitcase", "backpack"]:
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
                        if base_point[1] < prev_y - 30:
                            status = "WARNING"
                            box_color = (0, 0, 255)
                            display_label = "WRONG DIRECTION"

                    self.object_history[obj_id] = base_point

                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), box_color, 2)
                    label_size, _ = cv2.getTextSize(f"{display_label}", cv2.FONT_HERSHEY_DUPLEX, 0.5, 1)
                    cv2.rectangle(annotated_frame, (x1, y1 - 25), (x1 + label_size[0] + 10, y1), box_color, -1)
                    cv2.putText(annotated_frame, f"{display_label}", (x1 + 5, y1 - 8),
                                cv2.FONT_HERSHEY_DUPLEX, 0.5, (255, 255, 255), 1)

                    if status in ["DANGER", "WARNING"]:
                        alert_key = f"{camera_id}_{obj_id}_{status}"
                        if time.time() - self.last_alert_time.get(alert_key, 0) > 5:
                            new_det = Detection(
                                camera_id=camera_id,
                                detection_type=display_label,
                                confidence=float(conf),
                                priority="Critical" if status == "DANGER" else "High",
                                is_violation=True,
                                violation_type=status
                            )
                            repo.save_detection(new_det)
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
                        "camera_id": str(camera_id)
                   }
                })

                cv2.rectangle(annotated_frame, (0, 0), (250, 80), (0, 0, 0), -1)
                cv2.putText(annotated_frame, f"FPS: {current_fps}", (15, 25), 0, 0.6, (0, 255, 0), 2)
                cv2.putText(annotated_frame, f"ACTIVE OBJS: {active_objs_count}", (15, 50), 0, 0.6, (255, 255, 255), 2)
                cv2.putText(annotated_frame, f"REC", (15, 72), 0, 0.5, (0, 0, 255), 2)
                cv2.circle(annotated_frame, (60, 68), 5, (0, 0, 255), -1)

                self.last_frames[str(camera_id)] = annotated_frame
                await asyncio.sleep(0.01)
        except Exception as exc:
            print(f"❌ [{camera_id}] unexpected termination: {type(exc).__name__}: {exc}")
        finally:
            if cap is not None:
                cap.release()
                print(f"📌 [{camera_id}] cap released and processing ended")
            self.last_frames.pop(str(camera_id), None)
            if own_db:
                local_db.close()


# تصدير نسخة المحرك الموحدة

ai_engine = AIProcessor(model_path="models/yolov8n.pt")