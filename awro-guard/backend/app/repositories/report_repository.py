from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date

from ..models.models import Detection, Camera


class ReportRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_dashboard_data(
        self,
        start_date: date,
        end_date: date,
        camera_id: str | None = None,
        owner_id: str | None = None,
        is_admin: bool = False,
    ):
        query = self.db.query(Detection)

        query = query.filter(
            func.date(Detection.detected_at) >= start_date,
            func.date(Detection.detected_at) <= end_date,
        )

        if camera_id:
            query = query.filter(
                Detection.camera_id == camera_id
            )
        if owner_id and not is_admin:
            query = query.filter(Detection.owner_id == owner_id)

        total_detections = query.count()

        critical_alerts = query.filter(
            Detection.priority == "Critical"
        ).count()

        high_alerts = query.filter(
            Detection.priority == "High"
        ).count()

        normal_events = total_detections - critical_alerts - high_alerts

        # آخر التنبيهات
        latest_alerts = (
            query.order_by(
                Detection.detected_at.desc()
            )
            .limit(10)
            .all()
        )

        # الرسم البياني بالساعة
        hourly_stats = (
            self.db.query(
                func.to_char(
                    Detection.detected_at,
                    "HH24:00",
                ).label("hour"),
                func.count(
                    Detection.detection_id
                ).label("count"),
            )
            .group_by("hour")
            .order_by("hour")
            .all()
        )

        # توزيع الكاميرات
        camera_distribution_query = (
            self.db.query(
                Camera.camera_name,
                func.count(
                    Detection.detection_id
                ).label("count"),
            )
            .join(
                Detection,
                Camera.camera_id == Detection.camera_id,
            )
            .group_by(Camera.camera_name)
        )

        if owner_id and not is_admin:
            camera_distribution = camera_distribution_query.filter(Camera.owner_id == owner_id).all()
        else:
            camera_distribution = camera_distribution_query.all()

        # توزيع أنواع التهديد
        threat_distribution = (
            self.db.query(
                Detection.detection_type,
                func.count(
                    Detection.detection_id
                ).label("count"),
            )
            .group_by(
                Detection.detection_type
            )
            .all()
        )

        return {
            "summary": {
                "total_detections": total_detections,
                "critical_alerts": critical_alerts,
                "high_alerts": high_alerts,
                "normal_events": normal_events,
            },
            "charts": {
                "hourly": [
                    {
                        "hour": h.hour,
                        "count": h.count,
                    }
                    for h in hourly_stats
                ],
                "camera_distribution": [
                    {
                        "camera": c.camera_name,
                        "count": c.count,
                    }
                    for c in camera_distribution
                ],
                "threat_distribution": [
                    {
                        "type": t.detection_type,
                        "count": t.count,
                    }
                    for t in threat_distribution
                ],
            },
            "latest_alerts": [
                {
                    "type": d.detection_type,
                    "camera_id": str(d.camera_id),
                    "priority": d.priority,
                    "confidence": d.confidence,
                    "time": d.detected_at,
                }
                for d in latest_alerts
            ],
        }