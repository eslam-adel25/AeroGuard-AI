from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.models import Base, Detection, Camera
from app.services.report_service import ReportService


def test_get_report_stats_returns_dashboard_payload():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        camera = Camera(
            camera_id="cam-1",
            camera_name="Front Gate",
            location="Gate",
            status="online",
            owner_id="user-1",
        )
        db.add(camera)
        db.add(
            Detection(
                detection_id="det-1",
                camera_id="cam-1",
                owner_id="user-1",
                detection_type="weapon detected",
                priority="Critical",
                confidence=0.95,
                detected_at="2024-01-10T12:00:00",
                is_violation=True,
                violation_type="restricted area",
            )
        )
        db.add(
            Detection(
                detection_id="det-2",
                camera_id="cam-1",
                owner_id="user-1",
                detection_type="person detected",
                priority="Low",
                confidence=0.80,
                detected_at="2024-01-10T12:30:00",
                is_violation=False,
            )
        )
        db.commit()

        payload = ReportService.get_report_stats(
            db,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            owner_id="user-1",
            is_admin=False,
        )

        assert payload["summary"]["weapons"] == 1
        assert payload["summary"]["persons"] == 1
        assert payload["summary"]["active_cameras"] == 1
        assert payload["summary"]["ai_accuracy"] is not None
        assert payload["charts"]["frequency_by_zone"][0]["name"] == "Front Gate"
