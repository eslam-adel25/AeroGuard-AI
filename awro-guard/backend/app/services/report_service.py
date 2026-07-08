from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import date
from ..models.models import Detection, Camera


def _normalize_severity(priority: str | None) -> str:
    value = (priority or "").strip().lower()
    if value == "critical":
        return "Critical"
    if value == "high":
        return "High"
    if value == "medium":
        return "Medium"
    if value == "low":
        return "Low"
    return "Low"


def _category_from_detection_type(detection_type: str | None) -> str | None:
    value = (detection_type or "").strip().lower()

    if any(token in value for token in ["weapon", "gun", "knife"]):
        return "weapons"
    if any(token in value for token in ["fire", "smoke", "flame"]):
        return "fire"
    if any(token in value for token in ["person", "human", "intruder"]):
        return "persons"
    if any(token in value for token in ["vehicle", "car", "truck", "bus"]):
        return "vehicles"

    return None

class ReportService:
    @staticmethod
    def get_report_stats(db: Session, start_date: date, end_date: date, camera_id: str = None):
        """منطق استخراج الإحصائيات من قاعدة البيانات (Section 4)."""
        filters = [
            func.date(Detection.detected_at) >= start_date,
            func.date(Detection.detected_at) <= end_date
        ]
        if camera_id:
            filters.append(Detection.camera_id == camera_id)

        # 1. إجمالي الاكتشافات
        total = db.query(func.count(Detection.detection_id)).filter(and_(*filters)).scalar() or 0

        # 2. مخالفات المناطق المحظورة
        violations = db.query(func.count(Detection.detection_id)).filter(
            and_(*filters, Detection.is_violation.is_(True))
        ).scalar() or 0

        # 3. توزيع الأنواع (تهديدات)
        threat_rows = db.query(
            Detection.detection_type, func.count(Detection.detection_id)
        ).filter(and_(*filters)).group_by(Detection.detection_type).all()

        # 4. متوسط الثقة
        avg_conf = db.query(func.avg(Detection.confidence)).filter(and_(*filters)).scalar() or 0

        # 5. توزيع الأولويات
        severity_rows = db.query(
            Detection.priority,
            func.count(Detection.detection_id),
        ).filter(and_(*filters)).group_by(Detection.priority).all()

        severity_counts = {
            "Critical": 0,
            "High": 0,
            "Medium": 0,
            "Low": 0,
        }
        for priority, count in severity_rows:
            severity_counts[_normalize_severity(priority)] += int(count or 0)

        # 6. تجميع الأنواع التشغيلية المطلوبة في الـ KPI
        categorized_counts = {
            "weapons": 0,
            "fire": 0,
            "persons": 0,
            "vehicles": 0,
        }

        details = []
        for detection_type, count in threat_rows:
            c = int(count or 0)
            details.append({"type": detection_type, "count": c})

            bucket = _category_from_detection_type(detection_type)
            if bucket:
                categorized_counts[bucket] += c

        # 7. قائمة الكاميرات (للفلترة + الإحصاء)
        camera_query = db.query(
            Camera.camera_id,
            Camera.camera_name,
            Camera.location,
            Camera.status,
        )
        if camera_id:
            camera_query = camera_query.filter(Camera.camera_id == camera_id)
        camera_rows = camera_query.order_by(Camera.camera_name.asc()).all()

        cameras = [
            {
                "camera_id": str(c.camera_id),
                "camera_name": c.camera_name,
                "location": c.location,
                "status": c.status,
            }
            for c in camera_rows
        ]

        # 8. أكثر الكاميرات نشاطاً
        top_camera_rows = db.query(
            Camera.camera_id,
            Camera.camera_name,
            Camera.location,
            Camera.status,
            func.count(Detection.detection_id).label("count"),
        ).join(
            Detection,
            Camera.camera_id == Detection.camera_id,
        ).filter(
            and_(*filters),
        ).group_by(
            Camera.camera_id,
            Camera.camera_name,
            Camera.location,
            Camera.status,
        ).order_by(
            func.count(Detection.detection_id).desc(),
        ).limit(10).all()

        top_cameras = [
            {
                "camera_id": str(row.camera_id),
                "camera_name": row.camera_name,
                "location": row.location,
                "status": row.status,
                "count": int(row.count or 0),
            }
            for row in top_camera_rows
        ]

        # 9. التنبيهات الأخيرة
        recent_rows = db.query(
            Detection.detected_at,
            Detection.detection_type,
            Detection.confidence,
            Detection.priority,
            Detection.camera_id,
            Camera.camera_name,
        ).join(
            Camera,
            Camera.camera_id == Detection.camera_id,
        ).filter(
            and_(*filters),
        ).order_by(
            Detection.detected_at.desc(),
        ).limit(20).all()

        recent_alerts = [
            {
                "time": row.detected_at,
                "camera_id": str(row.camera_id),
                "camera_name": row.camera_name,
                "detection_type": row.detection_type,
                "confidence": float(row.confidence or 0),
                "severity": _normalize_severity(row.priority),
            }
            for row in recent_rows
        ]

        # 10. مخطط زمني حسب اليوم/الساعة
        timeline_rows = db.query(
            func.date(Detection.detected_at).label("day"),
            func.extract("hour", Detection.detected_at).label("hour"),
            func.count(Detection.detection_id).label("count"),
        ).filter(
            and_(*filters),
        ).group_by(
            func.date(Detection.detected_at),
            func.extract("hour", Detection.detected_at),
        ).order_by(
            func.date(Detection.detected_at),
            func.extract("hour", Detection.detected_at),
        ).all()

        timeline = [
            {
                "label": f"{row.day} {int(row.hour):02d}:00",
                "day": str(row.day),
                "hour": int(row.hour),
                "count": int(row.count or 0),
            }
            for row in timeline_rows
        ]

        # 11. Heatmap: كثافة حسب الساعة
        heatmap_rows = db.query(
            func.extract("hour", Detection.detected_at).label("hour"),
            func.count(Detection.detection_id).label("count"),
        ).filter(
            and_(*filters),
        ).group_by(
            func.extract("hour", Detection.detected_at),
        ).order_by(
            func.extract("hour", Detection.detected_at),
        ).all()

        heatmap = [
            {
                "hour": int(row.hour),
                "label": f"{int(row.hour):02d}:00",
                "count": int(row.count or 0),
            }
            for row in heatmap_rows
        ]

        # 12. توزيع الشدة بالنسبة المئوية
        severity_distribution = []
        for key in ["Critical", "High", "Medium", "Low"]:
            count = severity_counts[key]
            pct = round((count / total) * 100, 2) if total else 0
            severity_distribution.append(
                {
                    "severity": key,
                    "count": count,
                    "percentage": pct,
                }
            )

        active_cameras = sum(1 for c in cameras if (c.get("status") or "").lower() == "online")

        return {
            "summary": {
                # Backward-compatible keys (existing Reports page)
                "total": total,
                "violations": violations,
                "unknown_persons": 0,
                "average_confidence": round(float(avg_conf), 2),

                # Extended dashboard keys
                "total_detections": total,
                "critical_alerts": severity_counts["Critical"],
                "high_alerts": severity_counts["High"],
                "medium_alerts": severity_counts["Medium"],
                "low_alerts": severity_counts["Low"],
                "weapons": categorized_counts["weapons"],
                "fire": categorized_counts["fire"],
                "persons": categorized_counts["persons"],
                "vehicles": categorized_counts["vehicles"],
                "active_cameras": active_cameras,
                "ai_accuracy": None,
            },
            "details": details,
            "charts": {
                "timeline": timeline,
                "threat_distribution": details,
                "severity_distribution": severity_distribution,
                "top_cameras": top_cameras,
                "heatmap": heatmap,
            },
            "recent_alerts": recent_alerts,
            "cameras": cameras,
        }