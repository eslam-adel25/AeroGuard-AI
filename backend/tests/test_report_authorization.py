from datetime import date, datetime, time

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.v1 import reports
from app.core.security import create_access_token
from app.database.session import Base, get_db
from app.models.models import AIEvent, Camera, CustomerProfile, Report, Role, User


def test_report_exports_only_include_resources_owned_by_report_customer(
    monkeypatch, tmp_path
):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        role = Role(role_name="Admin")
        db.add(role)
        db.flush()
        customer = User(
            full_name="Report customer",
            username="report_customer",
            email="report_customer@example.com",
            password_hash="not-used",
            role_id=role.role_id,
            status="Active",
            is_verified=True,
        )
        other = User(
            full_name="Other customer",
            username="other_customer",
            email="other_customer@example.com",
            password_hash="not-used",
            role_id=role.role_id,
            status="Active",
            is_verified=True,
        )
        customer.customer_profile = CustomerProfile(
            workflow_status="PLATFORM_CUSTOMER",
            account_status="ACTIVE",
            all_features=True,
        )
        other.customer_profile = CustomerProfile(
            workflow_status="PLATFORM_CUSTOMER",
            account_status="ACTIVE",
            all_features=True,
        )
        db.add_all([customer, other])
        db.flush()
        customer.customer_profile_id = customer.customer_profile.customer_profile_id
        other.customer_profile_id = other.customer_profile.customer_profile_id
        db.flush()

        own_camera = Camera(
            camera_name="Own camera",
            location="Customer site",
            stream_url="0",
            camera_type="USB",
            owner_id=customer.user_id,
        )
        other_camera = Camera(
            camera_name="Other camera",
            location="Other site",
            stream_url="0",
            camera_type="USB",
            owner_id=other.user_id,
        )
        db.add_all([own_camera, other_camera])
        db.flush()

        today = date.today()
        own_event = AIEvent(
            camera_id=own_camera.camera_id,
            detected_by=customer.user_id,
            detection_type="own-event-marker",
            severity="Low",
            created_at=datetime.combine(today, time(12)),
        )
        other_event = AIEvent(
            camera_id=other_camera.camera_id,
            detected_by=other.user_id,
            detection_type="foreign-event-marker",
            severity="Critical",
            created_at=datetime.combine(today, time(12)),
        )
        db.add_all([own_event, other_event])
        report = Report(
            owner_id=customer.user_id,
            generated_by=customer.user_id,
            customer_profile_id=customer.customer_profile.customer_profile_id,
            title="Customer report",
            filters={"start_date": today.isoformat(), "end_date": today.isoformat()},
            summary={},
            charts={},
            details=[],
        )
        manipulated_report = Report(
            owner_id=customer.user_id,
            generated_by=customer.user_id,
            customer_profile_id=customer.customer_profile.customer_profile_id,
            title="Camera scope test",
            filters={"camera_id": str(other_camera.camera_id)},
            summary={},
            charts={},
            details=[],
        )
        db.add_all([report, manipulated_report])
        db.commit()
        user_id = str(customer.user_id)
        report_id = str(report.report_id)
        manipulated_report_id = str(manipulated_report.report_id)

    app = FastAPI()
    app.include_router(reports.router, prefix="/api/v1")

    def override_get_db():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    headers = {
        "Authorization": f"Bearer {create_access_token({'user_id': user_id})}"
    }

    try:
        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/reports/export/csv?report_id={report_id}",
                headers=headers,
            )

        assert response.status_code == 200
        assert "own-event-marker" in response.text
        assert "foreign-event-marker" not in response.text

        generated_pdf = tmp_path / "report.pdf"
        generated_pdf.write_bytes(b"synthetic pdf")
        observed_camera_scopes = []

        def capture_pdf_data(data, _filename):
            observed_camera_scopes.append(data["metadata"]["camera"])
            return str(generated_pdf)

        monkeypatch.setattr(
            reports.ReportGenerator, "generate_pdf", capture_pdf_data
        )
        monkeypatch.setattr(
            reports.ReportGenerator, "generate_pdf_with_ai", capture_pdf_data
        )
        pdf_response = client.get(
            f"/api/v1/reports/export/pdf?report_id={manipulated_report_id}",
            headers=headers,
        )

        assert pdf_response.status_code == 200
        assert pdf_response.content == b"synthetic pdf"
        assert observed_camera_scopes == [None, None]
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
