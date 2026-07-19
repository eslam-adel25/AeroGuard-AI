from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import date, datetime, timedelta
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
    if any(token in value for token in ["unknown", "suspicious", "unidentified", "object"]):
        return "suspicious_objects"

    return None


def _is_active_camera_status(status: str | None) -> bool:
    return (status or "").strip().lower() in {
        "processing",
        "streaming",
        "running",
        "connected",
    }

class ReportService:
    @staticmethod
    def get_report_stats(
        db: Session,
        start_date: date,
        end_date: date,
        camera_id: str = None,
        owner_id: str = None,
        is_admin: bool = False,
        detection_type: str | None = None,
        severity: str | None = None,
        confidence_min: float | None = None,
        confidence_max: float | None = None,
    ):
        """منطق استخراج الإحصائيات من قاعدة البيانات (Section 4)."""
        filters = [
            func.date(Detection.detected_at) >= start_date,
            func.date(Detection.detected_at) <= end_date,
        ]
        if camera_id:
            filters.append(Detection.camera_id == camera_id)
        if owner_id and not is_admin:
            filters.append(Detection.owner_id == owner_id)
        if detection_type:
            filters.append(Detection.detection_type.ilike(f"%{detection_type}%"))
        if severity:
            filters.append(Detection.priority.ilike(f"%{severity}%"))
        if confidence_min is not None:
            filters.append(Detection.confidence >= confidence_min)
        if confidence_max is not None:
            filters.append(Detection.confidence <= confidence_max)

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

        # 6. تجميع أنواع التفتيش التشغيلية المطلوبة
        categorized_counts = {
            "fire": 0,
            "smoke": 0,
            "weapons": 0,
            "persons": 0,
            "vehicles": 0,
            "suspicious_objects": 0,
            "restricted_area_violations": 0,
            "wrong_direction": 0,
            "loitering": 0,
            "crowd_density": 0,
            "abandoned_bag": 0,
            "unknown_persons": 0,
        }

        details = []
        for detection_type, count in threat_rows:
            c = int(count or 0)
            details.append({"type": detection_type, "count": c})

            bucket = _category_from_detection_type(detection_type)
            if bucket:
                categorized_counts[bucket] += c

            lower_type = (detection_type or "").lower()
            if "smoke" in lower_type:
                categorized_counts["smoke"] += c
            if "abandoned" in lower_type or "bag" in lower_type:
                categorized_counts["abandoned_bag"] += c
            if "loiter" in lower_type:
                categorized_counts["loitering"] += c
            if "crowd" in lower_type or "density" in lower_type:
                categorized_counts["crowd_density"] += c
            if "unknown" in lower_type and "person" in lower_type:
                categorized_counts["unknown_persons"] += c

        violation_counts = db.query(
            Detection.violation_type,
            func.count(Detection.detection_id),
        ).filter(and_(*filters, Detection.is_violation.is_(True))).group_by(Detection.violation_type).all()

        for violation_type, count in violation_counts:
            lower = (violation_type or "").lower()
            if "restricted" in lower:
                categorized_counts["restricted_area_violations"] += int(count or 0)
            elif "wrong" in lower or "direction" in lower:
                categorized_counts["wrong_direction"] += int(count or 0)

        max_conf = db.query(func.max(Detection.confidence)).filter(and_(*filters)).scalar() or 0
        min_conf = db.query(func.min(Detection.confidence)).filter(and_(*filters)).scalar() or 0

        # 7. قائمة الكاميرات (للفلترة + الإحصاء)
        camera_query = db.query(
            Camera.camera_id,
            Camera.camera_name,
            Camera.location,
            Camera.status,
        )
        if camera_id:
            camera_query = camera_query.filter(Camera.camera_id == camera_id)
        if owner_id and not is_admin:
            camera_query = camera_query.filter(Camera.owner_id == owner_id)
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
            (Camera.owner_id == owner_id) if (owner_id and not is_admin) else True,
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

        # 9. أكثر أنواع الاكتشاف نشاطاً
        top_types_rows = db.query(
            Detection.detection_type,
            func.count(Detection.detection_id).label("count"),
        ).filter(
            and_(*filters),
        ).group_by(
            Detection.detection_type,
        ).order_by(func.count(Detection.detection_id).desc()).limit(10).all()

        top_detection_types = [
            {"detection_type": row.detection_type, "count": int(row.count or 0)}
            for row in top_types_rows
        ]

        # 10. التنبيهات الأخيرة
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

        # 11. مخطط زمني حسب الفترة الزمنية المناسبة
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())
        span_days = (end_dt - start_dt).days + 1

        dialect_name = (
            db.bind.dialect.name
            if getattr(db, "bind", None) and getattr(db.bind, "dialect", None)
            else ""
        )

        if dialect_name == "sqlite":
            if span_days <= 1:
                bucket_value_expr = func.strftime("%Y-%m-%d %H:00:00", Detection.detected_at)
                label_expr = func.strftime("%H:00", Detection.detected_at)
            elif span_days <= 7:
                bucket_value_expr = func.strftime("%Y-%m-%d", Detection.detected_at)
                label_expr = func.strftime("%m-%d", Detection.detected_at)
            else:
                bucket_value_expr = func.strftime("%Y-%W", Detection.detected_at)
                label_expr = func.strftime("%Y-%W", Detection.detected_at)
        else:
            if span_days <= 1:
                bucket_value_expr = func.date_trunc("hour", Detection.detected_at)
                label_expr = func.to_char(bucket_value_expr, "HH24:00")
            elif span_days <= 7:
                bucket_value_expr = func.date_trunc("day", Detection.detected_at)
                label_expr = func.to_char(bucket_value_expr, "Mon DD")
            else:
                bucket_value_expr = func.date_trunc("week", Detection.detected_at)
                label_expr = func.to_char(bucket_value_expr, "Mon DD")

        timeline_rows = (
            db.query(
                bucket_value_expr.label("bucket_value"),
                label_expr.label("label"),
                Camera.camera_id.label("camera_id"),
                Camera.camera_name.label("camera_name"),
                func.count(Detection.detection_id).label("count"),
            )
            .join(Camera, Camera.camera_id == Detection.camera_id)
            .filter(and_(*filters))
            .group_by(
                bucket_value_expr,
                label_expr,
                Camera.camera_id,
                Camera.camera_name,
            )
            .order_by(bucket_value_expr, Camera.camera_name)
            .all()
        )

        timeline = []
        for row in timeline_rows:
            bucket_value = row.bucket_value
            if hasattr(bucket_value, "isoformat"):
                bucket_value = bucket_value.isoformat()
            elif bucket_value is None:
                bucket_value = ""
            else:
                bucket_value = str(bucket_value)

            timeline.append(
                {
                    "bucket_value": bucket_value,
                    "label": row.label,
                    "camera_id": str(row.camera_id),
                    "camera_name": row.camera_name,
                    "count": int(row.count or 0),
                }
            )

        detection_times = db.query(Detection.detected_at).filter(and_(*filters)).all()

        heatmap = []
        for hour in range(24):
            hour_count = sum(1 for (detected_at,) in detection_times if detected_at and detected_at.hour == hour)
            heatmap.append(
                {
                    "hour": hour,
                    "label": f"{hour:02d}",
                    "count": hour_count,
                }
            )

        # 13. توزيع الشدة بالنسبة المئوية
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

        active_cameras = sum(
            1
            for c in cameras
            if _is_active_camera_status(c.get("status"))
        )

        zone_frequency_rows = db.query(
            Camera.camera_name,
            func.count(Detection.detection_id).label("count"),
        ).join(
            Detection,
            Camera.camera_id == Detection.camera_id,
        ).filter(and_(*filters)).group_by(Camera.camera_name).order_by(func.count(Detection.detection_id).desc()).all()

        zone_frequency = [
            {"name": row.camera_name, "count": int(row.count or 0)} for row in zone_frequency_rows
        ]

        return {
            "summary": {
                # Backward-compatible keys (existing Reports page)
                "total": total,
                "violations": violations,
                "unknown_persons": categorized_counts["unknown_persons"],
                "average_confidence": round(float(avg_conf), 2),

                # Extended dashboard keys
                "total_detections": total,
                "critical_alerts": severity_counts["Critical"],
                "high_alerts": severity_counts["High"],
                "medium_alerts": severity_counts["Medium"],
                "low_alerts": severity_counts["Low"],
                "fire": categorized_counts["fire"] + categorized_counts["smoke"],
                "suspicious_objects": categorized_counts["suspicious_objects"],
                "weapons": categorized_counts["weapons"],
                "persons": categorized_counts["persons"],
                "vehicles": categorized_counts["vehicles"],
                "fire_detections": categorized_counts["fire"],
                "smoke_detections": categorized_counts["smoke"],
                "weapon_detections": categorized_counts["weapons"],
                "person_detections": categorized_counts["persons"],
                "vehicle_detections": categorized_counts["vehicles"],
                "restricted_area_violations": categorized_counts["restricted_area_violations"],
                "wrong_direction_events": categorized_counts["wrong_direction"],
                "loitering_events": categorized_counts["loitering"],
                "crowd_density_alerts": categorized_counts["crowd_density"],
                "abandoned_bag_events": categorized_counts["abandoned_bag"],
                "max_confidence": float(max_conf),
                "min_confidence": float(min_conf),
                "average_confidence": round(float(avg_conf or 0) * 100, 2) if avg_conf is not None else 0,
                "active_cameras": active_cameras,
            },
            "details": details,
            "charts": {
                "timeline": timeline,
                "threat_distribution": details,
                "severity_distribution": severity_distribution,
                "top_cameras": top_cameras,
                "top_detection_types": top_detection_types,
                "heatmap": heatmap,
                "frequency_by_zone": zone_frequency,
            },
            "recent_alerts": recent_alerts,
            "cameras": cameras,
        }

    @staticmethod
    def generate_report(
        db: Session,
        start_date: date,
        end_date: date,
        camera_id: str | None,
        owner_id: str,
        generated_by: str,
        title: str | None = None,
        report_type: str = "custom",
        detection_type: str | None = None,
        severity: str | None = None,
        confidence_min: float | None = None,
        confidence_max: float | None = None,
        extra_filters: dict | None = None,
        is_admin: bool = False,
    ):
        # reuse get_report_stats to produce payload
        payload = ReportService.get_report_stats(
            db,
            start_date,
            end_date,
            camera_id=camera_id,
            owner_id=owner_id,
            is_admin=is_admin,
            detection_type=detection_type,
            severity=severity,
            confidence_min=confidence_min,
            confidence_max=confidence_max,
        )

        # persist report
        from ..repositories.report_repository import ReportRepository

        repo = ReportRepository(db)
        filters = {
            "start_date": str(start_date),
            "end_date": str(end_date),
            "camera_id": camera_id,
            "detection_type": detection_type,
            "severity": severity,
            "confidence_min": confidence_min,
            "confidence_max": confidence_max,
        }
        if extra_filters:
            filters.update(extra_filters)

        report = repo.create_report_record(owner_id=owner_id, generated_by=generated_by, title=title, report_type=report_type, filters=filters, payload=payload)
        return report