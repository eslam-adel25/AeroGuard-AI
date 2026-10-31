from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_, cast
from sqlalchemy.types import String
from datetime import date
import logging

from ..models.models import Detection, Camera, Report
from ..models.models import AIEvent
from .ai_repository import AIRepository
from ..core.tenant import (
    PLATFORM_TENANT_SCOPE,
    tenant_camera_child_filter,
    tenant_camera_ids,
    tenant_member_user_ids,
)

logger = logging.getLogger(__name__)


class ReportRepository:
    def __init__(self, db: Session):
        self.db = db

    # Persistent reports storage
    def create_report_record(
        self,
        owner_id: str,
        generated_by: str,
        title: str | None,
        report_type: str,
        filters: dict,
        payload: dict,
        customer_profile_id: str | None = None,
    ):
        report = Report(
            owner_id=owner_id,
            customer_profile_id=customer_profile_id,
            generated_by=generated_by,
            title=title,
            report_type=report_type,
            filters=filters,
            summary=payload.get("summary") if payload else None,
            charts=payload.get("charts") if payload else None,
            details=payload.get("details") if payload else None,
            export_history=[],
        )
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        return report

    def get_report(
        self,
        report_id: str,
        owner_id: str | None = None,
        is_admin: bool = False,
        customer_profile_id: str | None = None,
    ):
        q = self.db.query(Report).filter(Report.report_id == report_id)
        if customer_profile_id == PLATFORM_TENANT_SCOPE:
            pass
        elif customer_profile_id:
            q = q.filter(Report.customer_profile_id == customer_profile_id)
            if q.first() is None:
                member_ids = tenant_member_user_ids(self.db, customer_profile_id)
                unresolved = (
                    self.db.query(Report.report_id)
                    .filter(
                        Report.report_id == report_id,
                        Report.customer_profile_id.is_(None),
                        or_(
                            Report.owner_id.in_(member_ids),
                            Report.generated_by.in_(member_ids),
                        ),
                    )
                    .first()
                )
                if unresolved:
                    logger.warning(
                        "Denied access to report %s without verified tenant ownership",
                        report_id,
                    )
                return None
        elif owner_id and not is_admin:
            q = q.filter(Report.owner_id == owner_id)
        else:
            q = q.filter(False)
        return q.first()

    def list_reports(
        self,
        owner_id: str | None = None,
        is_admin: bool = False,
        limit: int = 50,
        offset: int = 0,
        query: str | None = None,
        camera_id: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        customer_profile_id: str | None = None,
    ):
        q = self.db.query(Report)
        if customer_profile_id == PLATFORM_TENANT_SCOPE:
            pass
        elif customer_profile_id:
            q = q.filter(Report.customer_profile_id == customer_profile_id)
            member_ids = tenant_member_user_ids(self.db, customer_profile_id)
            unresolved_count = (
                self.db.query(func.count(Report.report_id))
                .filter(
                    Report.customer_profile_id.is_(None),
                    or_(
                        Report.owner_id.in_(member_ids),
                        Report.generated_by.in_(member_ids),
                    ),
                )
                .scalar()
                or 0
            )
            if unresolved_count:
                logger.warning(
                    "Customer %s has %s reports without verified tenant ownership",
                    customer_profile_id,
                    unresolved_count,
                )
        elif owner_id and not is_admin:
            q = q.filter(Report.owner_id == owner_id)
        else:
            q = q.filter(False)
        if query:
            q = q.filter(
                or_(
                    Report.report_id.ilike(f"%{query}%"),
                    Report.title.ilike(f"%{query}%"),
                    cast(Report.details, String).ilike(f"%{query}%"),
                )
            )
        if camera_id:
            q = q.filter(Report.filters["camera_id"].astext == camera_id)
        if start_date:
            q = q.filter(Report.generated_at >= start_date)
        if end_date:
            q = q.filter(Report.generated_at <= end_date)
        total = q.count()
        rows = q.order_by(desc(Report.generated_at)).limit(limit).offset(offset).all()
        return {
            "total": total,
            "items": rows,
        }

    def delete_report(
        self,
        report_id: str,
        owner_id: str | None = None,
        is_admin: bool = False,
        customer_profile_id: str | None = None,
    ):
        report = self.get_report(
            report_id,
            owner_id=owner_id,
            is_admin=is_admin,
            customer_profile_id=customer_profile_id,
        )
        if not report:
            return False
        self.db.delete(report)
        self.db.commit()
        return True

    def append_export_history(self, report: Report, export_entry: dict):
        history = report.export_history or []
        history.append(export_entry)
        report.export_history = history
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        return report


    def get_dashboard_data(
        self,
        start_date: date,
        end_date: date,
        camera_id: str | None = None,
        owner_id: str | None = None,
        is_admin: bool = False,
        customer_profile_id: str | None = None,
    ):
        filters = [
            func.date(Detection.detected_at) >= start_date,
            func.date(Detection.detected_at) <= end_date,
        ]
        if camera_id:
            filters.append(Detection.camera_id == camera_id)
        if customer_profile_id:
            filters.append(
                Detection.camera_id.in_(
                    tenant_camera_ids(self.db, customer_profile_id)
                )
            )
            filters.append(
                tenant_owner_filter(
                    Detection,
                    self.db,
                    customer_profile_id,
                    Detection.owner_id,
                )
            )
        elif owner_id and not is_admin:
            filters.append(Detection.owner_id == owner_id)
        else:
            filters.append(False)
        query = self.db.query(Detection).filter(*filters)

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
            .filter(*filters)
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
            .filter(*filters)
            .group_by(Camera.camera_name)
        )

        if customer_profile_id:
            camera_distribution = camera_distribution_query.filter(
                tenant_owner_filter(
                    Camera,
                    self.db,
                    customer_profile_id,
                    Camera.owner_id,
                )
            ).all()
        elif owner_id and not is_admin:
            camera_distribution = camera_distribution_query.filter(Camera.owner_id == owner_id).all()
        else:
            camera_distribution = camera_distribution_query.filter(False).all()

        # توزيع أنواع التهديد
        threat_distribution = (
            self.db.query(
                Detection.detection_type,
                func.count(
                    Detection.detection_id
                ).label("count"),
            )
            .filter(*filters)
            .group_by(
                Detection.detection_type
            )
            .all()
        )

        # include AI events distribution (fires, smoke, loitering, etc.)
        ai_distribution = (
            self.db.query(
                AIEvent.detection_type,
                func.count(AIEvent.event_id).label("count"),
            )
            .filter(
                tenant_camera_child_filter(
                    AIEvent,
                    self.db,
                    customer_profile_id,
                    actor_column=AIEvent.detected_by,
                )
                if customer_profile_id
                else (
                    AIEvent.detected_by == owner_id
                    if owner_id and not is_admin
                    else False
                )
            )
            .group_by(AIEvent.detection_type)
        )
        ai_distribution = AIRepository.exclude_pending_events(ai_distribution).all()

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
                "ai_events": [
                    {
                        "type": a.detection_type,
                        "count": a.count,
                    }
                    for a in ai_distribution
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