import cv2
import asyncio
import time
import numpy as np
from ultralytics import YOLO
from sqlalchemy.orm import Session
from ..models.models import Detection, Camera, RestrictedZone, SystemSettings
from ..repositories.detection_repository import DetectionRepository
from ..services.decision_engine import DecisionEngine
from ..websocket.manager import manager

class AIProcessor:
    def __init__(self, model_path: str):
        # تحميل الموديل لمرة واحدة عند التشغيل (صفحة 163)
        self.model = YOLO(model_path)
        self.decision_engine = DecisionEngine()
        
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

    async def process_camera(self, camera_id, rtsp_url, db: Session):
        """المحرك الشامل: معالجة البث الحي أو الفيديوهات المرفوعة (Section 5 & 13)"""
        
        # 1. تحديد نوع المصدر ومعالجته
        source = 0 if str(rtsp_url) == "0" else rtsp_url
        cap = cv2.VideoCapture(source, cv2.CAP_DSHOW) if source == 0 else cv2.VideoCapture(source)
        
        # 2. تحميل إعدادات المناطق المحظورة
        zones = db.query(RestrictedZone).filter(RestrictedZone.camera_id == camera_id).all()
        
        # 3. التحقق من الإعدادات
        if not self.active_settings:
            self.active_settings = db.query(SystemSettings).first()
        
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

        repo = DetectionRepository(db)
        print(f"🛡️ AeroGuard Monitoring Initiated: {camera_id}")

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                # إذا كان فيديو مرفوع (Section 5) وانتهى، نغلق العملية
                if isinstance(source, str) and not source.isdigit(): 
                    print(f"✅ Video processing completed: {camera_id}")
                    break
                await asyncio.sleep(1)
                continue

            start_time = time.time()

            # 4. تشغيل YOLOv8 مع التتبع (Tracking Enabled من الإعدادات)
            # ندعم الشخص والحقائب (Section 13)
            results = await asyncio.to_thread(
                self.model.track, 
                frame, 
                persist=True, 
                conf=conf_thr, 
                verbose=False,
                tracker="botsort.yaml" # أدق خوارزمية تتبع للمطارات
            )
            print(results[0].boxes)
            
            annotated_frame = frame.copy()
            active_objs_count = 0

            if results[0].boxes.id is not None:
                boxes = results[0].boxes.xyxy.cpu().numpy()
                ids = results[0].boxes.id.cpu().numpy().astype(int)
                labels = results[0].boxes.cls.cpu().numpy().astype(int)
                confs = results[0].boxes.conf.cpu().numpy()

                for box, obj_id, cls_idx, conf in zip(boxes, ids, labels, confs):
                    if active_objs_count >= max_objs: break
                    
                    label_name = self.model.names[cls_idx].lower()
                    print("Detected:", label_name)
                    # الفلترة بناءً على الأصناف المطلوبة (Section 13)
                    if label_name not in ["person", "bag", "suitcase", "backpack"]: continue
                    
                    active_objs_count += 1
                    print("Objects:", active_objs_count)
                    x1, y1, x2, y2 = box.astype(int)
                    base_point = (int((x1 + x2) / 2), y2) # نقطة الارتكاز (القدمين)
                    
                    # القيم الافتراضية للرسم (Section 6)
                    status = "NORMAL"
                    box_color = (0, 255, 0) # Green
                    display_label = "Person" if label_name == "person" else "Baggage"

                    # 5. منطق المناطق المحظورة (Polygon Logic - Section 7)
                    in_restricted = False
                    for zone in zones:
                        polygon = np.array(zone.polygon_coords, np.int32)
                        # رسم حدود المنطقة دائماً للشفافية
                        cv2.polylines(annotated_frame, [polygon], True, (255, 255, 255), 1)
                        
                        if cv2.pointPolygonTest(polygon, base_point, False) >= 0:
                            in_restricted = True
                            status = "DANGER"
                            box_color = (0, 0, 255) # Red
                            display_label = f"RESTRICTED AREA"
                            break

                    # 6. منطق عكس الاتجاه (Wrong Direction - Section 7)
                    if obj_id in self.object_history and not in_restricted:
                        prev_y = self.object_history[obj_id][1]
                        # إذا كان يتحرك للأعلى بشكل كبير (مثال لاتجاه الخروج)
                        if base_point[1] < prev_y - 30: 
                            status = "WARNING"
                            box_color = (0, 0, 255) # Red Box as per Section 6
                            display_label = "WRONG DIRECTION"
                    
                    self.object_history[obj_id] = base_point

                    # 7. التعرف على المجهولين (Unknown Person - Section 6)
                    # سيتم ربطها بـ DeepFace لاحقاً، حالياً أي شخص غير مسجل هو Unknown
                    if label_name == "person" and status == "NORMAL":
                        # تجريبي: إذا كان لا يملك ID معروف
                        pass 

                    # 8. الرسم المتقدم (HUD Overlay - Section 6)
                    # رسم المربع
                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), box_color, 2)
                    
                    # رسم التسمية الخلفية (Label Background)
                    label_size, _ = cv2.getTextSize(f"{display_label}", cv2.FONT_HERSHEY_DUPLEX, 0.5, 1)
                    cv2.rectangle(annotated_frame, (x1, y1 - 25), (x1 + label_size[0] + 10, y1), box_color, -1)
                    cv2.putText(annotated_frame, f"{display_label}", (x1 + 5, y1 - 8), 
                                cv2.FONT_HERSHEY_DUPLEX, 0.5, (255, 255, 255), 1)

                    # 9. تخزين التجاوزات فقط (Section 10 & 11)
                    if status in ["DANGER", "WARNING"]:
                        alert_key = f"{camera_id}_{obj_id}_{status}"
                        # إرسال تنبيه كل 5 ثواني لنفس الكائن لمنع ازدحام البيانات
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
                            
                            # البث للداشبورد فقط (إلغاء SMS/Email) كما هو مطلوب
                            await manager.broadcast({
                                "event": "new_alert",
                                "data": {
                                    "type": display_label,
                                    "priority": "Critical" if status == "DANGER" else "High",
                                    "camera_id": str(camera_id)
                                }
                            })
                            self.last_alert_time[alert_key] = time.time()

            # 10. واجهة المعلومات العلوية (HUD Stats - Section 6 & 9)
            elapsed = time.time() - start_time
            current_fps = int(1.0 / elapsed) if elapsed > 0 else 30
            
            await manager.broadcast({
                "event": "ai_status",
                "data": {
                    "fps": current_fps,
                    "objects": active_objs_count,
                    "camera_id": str(camera_id)
               }
            })
            
            # مستطيل المعلومات العلوي
            cv2.rectangle(annotated_frame, (0, 0), (250, 80), (0, 0, 0), -1)
            cv2.putText(annotated_frame, f"FPS: {current_fps}", (15, 25), 0, 0.6, (0, 255, 0), 2)
            cv2.putText(annotated_frame, f"ACTIVE OBJS: {active_objs_count}", (15, 50), 0, 0.6, (255, 255, 255), 2)
            cv2.putText(annotated_frame, f"REC", (15, 72), 0, 0.5, (0, 0, 255), 2)
            cv2.circle(annotated_frame, (60, 68), 5, (0, 0, 255), -1)

            # حفظ الفريم في الذاكرة للبث
            self.last_frames[str(camera_id)] = annotated_frame
            await asyncio.sleep(0.01)

        cap.release()
        self.last_frames.pop(str(camera_id), None)

# تصدير نسخة المحرك الموحدة
ai_engine = AIProcessor(model_path="models/yolov8n.pt")