import os
import uuid
from datetime import date, datetime

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.models import Base, Detection, Camera
from app.services.report_service import ReportService


def test_get_report_stats_returns_dashboard_payload():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        camera = Camera(
            camera_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            camera_name="Front Gate",
            location="Gate",
            stream_url="rtsp://example.com/stream",
            status="running",
            owner_id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
        )
        db.add(camera)
        db.add(
            Detection(
                detection_id=uuid.UUID("00000000-0000-0000-0000-000000000101"),
                camera_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
                owner_id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
                detection_type="weapon detected",
                priority="Critical",
                confidence=0.95,
                detected_at=datetime(2024, 1, 10, 12, 0, 0),
                is_violation=True,
                violation_type="restricted area",
            )
        )
        db.add(
            Detection(
                detection_id=uuid.UUID("00000000-0000-0000-0000-000000000102"),
                camera_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
                owner_id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
                detection_type="person detected",
                priority="Low",
                confidence=0.80,
                detected_at=datetime(2024, 1, 10, 12, 30, 0),
                is_violation=False,
            )
        )
        db.commit()

        payload = ReportService.get_report_stats(
            db,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            is_admin=True,
        )

        assert payload["summary"]["weapons"] == 1
        assert payload["summary"]["persons"] == 1
        assert payload["summary"]["active_cameras"] == 1
        assert payload["summary"]["average_confidence"] == 87.5
        assert payload["summary"]["fire"] == 0
        assert payload["summary"]["suspicious_objects"] == 0
        assert payload["charts"]["frequency_by_zone"][0]["name"] == "Front Gate"
        assert payload["charts"]["timeline"][0]["camera_name"] == "Front Gate"
        assert payload["charts"]["timeline"][0]["count"] == 2


def test_get_report_stats_counts_fire_and_smoke_detections():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        camera = Camera(
            camera_id=uuid.UUID("00000000-0000-0000-0000-000000000021"),
            camera_name="Fire Camera",
            location="Warehouse",
            stream_url="rtsp://example.com/fire",
            status="running",
            owner_id=uuid.UUID("00000000-0000-0000-0000-000000000022"),
        )
        db.add(camera)
        for index, detection_type in enumerate(("FIRE", "SMOKE"), start=1):
            db.add(
                Detection(
                    detection_id=uuid.UUID(
                        f"00000000-0000-0000-0000-0000000001{20 + index:02d}"
                    ),
                    camera_id=camera.camera_id,
                    owner_id=camera.owner_id,
                    detection_type=detection_type,
                    priority="Critical",
                    confidence=0.9,
                    detected_at=datetime(2024, 1, 10, 12, index, 0),
                    is_violation=True,
                    violation_type="DANGER",
                )
            )
        db.commit()

        payload = ReportService.get_report_stats(
            db,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            is_admin=True,
        )

        assert payload["summary"]["fire"] == 2
        assert payload["summary"]["fire_detections"] == 1
        assert payload["summary"]["smoke_detections"] == 1
        assert payload["summary"]["critical_alerts"] == 2


def test_unknown_priority_is_excluded_from_severity_distribution():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        camera = Camera(
            camera_id=uuid.UUID("00000000-0000-0000-0000-000000000011"),
            camera_name="Unknown Priority Camera",
            location="Gate",
            stream_url="rtsp://example.com/stream",
            status="running",
            owner_id=uuid.UUID("00000000-0000-0000-0000-000000000012"),
        )
        db.add(camera)
        db.add(
            Detection(
                detection_id=uuid.UUID("00000000-0000-0000-0000-000000000111"),
                camera_id=camera.camera_id,
                owner_id=camera.owner_id,
                detection_type="person detected",
                priority=None,
                confidence=0.8,
                detected_at=datetime(2024, 1, 10, 12, 0, 0),
                is_violation=False,
            )
        )
        db.commit()

        payload = ReportService.get_report_stats(
            db,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            is_admin=True,
        )

        assert payload["summary"]["low_alerts"] == 0
        assert sum(
            item["count"] for item in payload["charts"]["severity_distribution"]
        ) == 0
