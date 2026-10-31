import asyncio
from datetime import date, datetime
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.ai.processor import build_detection_record
from app.api.v1 import (
    ai as ai_api,
    cameras as cameras_api,
    reports as reports_api,
    users as users_api,
)
from app.api.v1.websocket_api import manager
from app.core.auth_middleware import ensure_user_can_access_platform
from app.core.security import create_access_token
from app.core.tenant import customer_profile_for_user
from app.database.session import Base, get_db
from app.models.models import (
    AIEvent,
    Camera,
    CustomerProfile,
    Detection,
    Report,
    Role,
    User,
)
from app.repositories.ai_repository import AIRepository
from app.repositories.camera_repository import CameraRepository
from app.repositories.report_repository import ReportRepository
from app.services.report_service import ReportService


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine, Session(engine)


def _admin(db, role, username):
    user = User(
        full_name=username,
        username=username,
        email=f"{username}@example.com",
        password_hash="test-hash",
        role=role,
        status="Active",
        is_verified=True,
    )
    profile = CustomerProfile(
        workflow_status="PLATFORM_CUSTOMER",
        account_status="ACTIVE",
        all_features=True,
    )
    user.customer_profile = profile
    db.add(user)
    db.flush()
    user.customer_profile_id = profile.customer_profile_id
    db.flush()
    return user, profile


def test_customer_analytics_and_resource_queries_are_tenant_scoped():
    engine, db = _session()
    try:
        admin_role = Role(role_name="Admin")
        db.add(admin_role)
        db.flush()
        admin_a, profile_a = _admin(db, admin_role, "tenant_a_admin")
        admin_b, profile_b = _admin(db, admin_role, "tenant_b_admin")

        camera_a = Camera(
            camera_name="A camera",
            location="A",
            stream_url="0",
            owner_id=admin_a.user_id,
            customer_profile_id=profile_a.customer_profile_id,
        )
        camera_b = Camera(
            camera_name="B camera",
            location="B",
            stream_url="0",
            owner_id=admin_b.user_id,
            customer_profile_id=profile_b.customer_profile_id,
        )
        db.add_all([camera_a, camera_b])
        db.flush()

        today = date(2026, 2, 1)
        db.add_all(
            [
                Detection(
                    camera_id=camera_a.camera_id,
                    owner_id=admin_a.user_id,
                    customer_profile_id=profile_a.customer_profile_id,
                    detection_type="person",
                    priority="High",
                    confidence=0.9,
                    detected_at=datetime(2026, 2, 1, 12),
                ),
                Detection(
                    camera_id=camera_b.camera_id,
                    owner_id=admin_b.user_id,
                    customer_profile_id=profile_b.customer_profile_id,
                    detection_type="fire",
                    priority="Critical",
                    confidence=0.99,
                    detected_at=datetime(2026, 2, 1, 12),
                ),
                AIEvent(
                    camera_id=camera_a.camera_id,
                    detected_by=admin_a.user_id,
                    customer_profile_id=profile_a.customer_profile_id,
                    detection_type="tenant-a-event",
                    severity="Low",
                ),
                AIEvent(
                    camera_id=camera_b.camera_id,
                    detected_by=admin_b.user_id,
                    customer_profile_id=profile_b.customer_profile_id,
                    detection_type="tenant-b-event",
                    severity="Critical",
                ),
                AIEvent(
                    camera_id=camera_b.camera_id,
                    detected_by=admin_a.user_id,
                    customer_profile_id=profile_a.customer_profile_id,
                    detection_type="mismatched-tenant-event",
                    severity="Low",
                ),
            ]
        )
        report_a = Report(
            owner_id=admin_a.user_id,
            generated_by=admin_a.user_id,
            customer_profile_id=profile_a.customer_profile_id,
            title="A report",
            filters={},
            summary={},
            charts={},
            details=[],
        )
        report_b = Report(
            owner_id=admin_b.user_id,
            generated_by=admin_b.user_id,
            customer_profile_id=profile_b.customer_profile_id,
            title="B report",
            filters={},
            summary={},
            charts={},
            details=[],
        )
        db.add_all([report_a, report_b])
        db.commit()

        cameras = CameraRepository(db).get_all_cameras(
            customer_profile_id=profile_a.customer_profile_id
        )
        assert [camera.camera_id for camera in cameras] == [camera_a.camera_id]

        ai_repo = AIRepository(db)
        events = ai_repo.list_events(
            customer_profile_id=profile_a.customer_profile_id
        )
        assert [event.detection_type for event in events] == ["tenant-a-event"]
        _, report_events = ai_repo.query_events_for_report(
            customer_profile_id=profile_a.customer_profile_id
        )
        assert [event["detection_type"] for event in report_events] == [
            "tenant-a-event"
        ]

        report_rows = ReportRepository(db).list_reports(
            customer_profile_id=profile_a.customer_profile_id
        )
        assert [report.title for report in report_rows["items"]] == ["A report"]
        stats = ReportService.get_report_stats(
            db,
            start_date=today,
            end_date=today,
            customer_profile_id=profile_a.customer_profile_id,
        )
        assert stats["summary"]["total_detections"] == 1
        assert stats["summary"]["high_alerts"] == 1
        assert stats["summary"]["critical_alerts"] == 0
        assert stats["cameras"] == [
            {
                "camera_id": str(camera_a.camera_id),
                "camera_name": "A camera",
                "location": "A",
                "status": camera_a.status,
            }
        ]
    finally:
        db.close()
        engine.dispose()


def test_platform_owner_can_manage_resources_across_customer_tenants():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    db = Session(engine)
    app = FastAPI()
    try:
        owner_role = Role(role_name="Owner")
        admin_role = Role(role_name="Admin")
        officer_role = Role(role_name="Officer")
        db.add_all([owner_role, admin_role, officer_role])
        db.flush()
        owner = User(
            full_name="Platform Owner",
            username="platform_owner",
            email="platform_owner@example.com",
            password_hash="test-hash",
            role=owner_role,
            status="Active",
            is_verified=True,
        )
        db.add(owner)
        admin_a, profile_a = _admin(db, admin_role, "owner_access_a")
        admin_b, profile_b = _admin(db, admin_role, "owner_access_b")
        profile_a.max_camera_count = 3
        profile_b.max_camera_count = 2
        camera_a = Camera(
            camera_name="Owner test A",
            location="A",
            stream_url="0",
            camera_type="USB",
            owner_id=admin_a.user_id,
            customer_profile_id=profile_a.customer_profile_id,
        )
        camera_b = Camera(
            camera_name="Owner test B",
            location="B",
            stream_url="0",
            camera_type="USB",
            owner_id=admin_b.user_id,
            customer_profile_id=profile_b.customer_profile_id,
        )
        db.add_all([camera_a, camera_b])
        db.flush()
        db.add_all(
            [
                Detection(
                    camera_id=camera_a.camera_id,
                    owner_id=admin_a.user_id,
                    customer_profile_id=profile_a.customer_profile_id,
                    detection_type="person",
                    priority="High",
                    confidence=0.9,
                    detected_at=datetime(2026, 2, 1, 12),
                ),
                Detection(
                    camera_id=camera_b.camera_id,
                    owner_id=admin_b.user_id,
                    customer_profile_id=profile_b.customer_profile_id,
                    detection_type="fire",
                    priority="Critical",
                    confidence=0.99,
                    detected_at=datetime(2026, 2, 1, 12),
                ),
            ]
        )
        event_a = AIEvent(
            camera_id=camera_a.camera_id,
            detected_by=admin_a.user_id,
            customer_profile_id=profile_a.customer_profile_id,
            detection_type="owner-test-a",
            severity="Low",
        )
        event_b = AIEvent(
            camera_id=camera_b.camera_id,
            detected_by=admin_b.user_id,
            customer_profile_id=profile_b.customer_profile_id,
            detection_type="owner-test-b",
            severity="High",
        )
        report_a = Report(
            owner_id=admin_a.user_id,
            generated_by=admin_a.user_id,
            customer_profile_id=profile_a.customer_profile_id,
            title="Owner test A",
            filters={},
            summary={},
            charts={},
            details=[],
        )
        report_b = Report(
            owner_id=admin_b.user_id,
            generated_by=admin_b.user_id,
            customer_profile_id=profile_b.customer_profile_id,
            title="Owner test B",
            filters={},
            summary={},
            charts={},
            details=[],
        )
        db.add_all([event_a, event_b, report_a, report_b])
        db.commit()
        owner_id = str(owner.user_id)
        admin_a_id = str(admin_a.user_id)
        profile_a_id = str(profile_a.customer_profile_id)
        profile_b_id = str(profile_b.customer_profile_id)
        event_b_id = str(event_b.event_id)
        report_b_id = str(report_b.report_id)
        officer_role_id = str(officer_role.role_id)
    finally:
        db.close()

    app.include_router(cameras_api.router)
    app.include_router(ai_api.router)
    app.include_router(reports_api.router)
    app.include_router(users_api.router)

    def override_get_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    owner_headers = {
        "Authorization": f"Bearer {create_access_token({'user_id': owner_id})}"
    }
    admin_headers = {
        "Authorization": f"Bearer {create_access_token({'user_id': admin_a_id})}"
    }
    try:
        with TestClient(app) as client:
            owner_cameras = client.get("/cameras/", headers=owner_headers)
            admin_cameras = client.get("/cameras/", headers=admin_headers)
            owner_events = client.get("/ai/events", headers=owner_headers)
            owner_analytics = client.get(
                "/reports/summary",
                params={"start_date": "2026-02-01", "end_date": "2026-02-01"},
                headers=owner_headers,
            )
            admin_analytics = client.get(
                "/reports/summary",
                params={"start_date": "2026-02-01", "end_date": "2026-02-01"},
                headers=admin_headers,
            )
            admin_cannot_get_b_event = client.get(
                f"/ai/events/{event_b_id}", headers=admin_headers
            )
            owner_reports = client.get("/reports/", headers=owner_headers)
            admin_reports = client.get("/reports/", headers=admin_headers)
            owner_can_get_b_report = client.get(
                f"/reports/{report_b_id}", headers=owner_headers
            )
            admin_cannot_get_b_report = client.get(
                f"/reports/{report_b_id}", headers=admin_headers
            )
            owner_can_export_b_report = client.get(
                "/reports/export/csv",
                params={"report_id": report_b_id},
                headers=owner_headers,
            )
            owner_users = client.get("/users/", headers=owner_headers)
            admin_users = client.get("/users/", headers=admin_headers)
            created_officer = client.post(
                "/users/",
                json={
                    "full_name": "Owner-created Officer",
                    "username": "owner_created_officer",
                    "email": "owner_created_officer@example.com",
                    "password": "StrongPass123!",
                    "phone": "555-0123",
                    "role_id": officer_role_id,
                    "customer_profile_id": profile_b_id,
                },
                headers=owner_headers,
            )
            admin_created_officer = client.post(
                "/users/",
                json={
                    "full_name": "Admin-created Officer",
                    "username": "admin_created_officer",
                    "email": "admin_created_officer@example.com",
                    "password": "StrongPass123!",
                    "phone": "555-0456",
                    "role_id": officer_role_id,
                    "customer_profile_id": profile_b_id,
                },
                headers=admin_headers,
            )
            created_camera = client.post(
                "/cameras/",
                data={
                    "camera_name": "Owner-created camera",
                    "location": "B",
                    "camera_type": "USB",
                    "customer_profile_id": profile_b_id,
                },
                headers=owner_headers,
            )
            over_quota_camera = client.post(
                "/cameras/",
                data={
                    "camera_name": "Over-quota camera",
                    "location": "B",
                    "camera_type": "USB",
                    "customer_profile_id": profile_b_id,
                },
                headers=owner_headers,
            )

        assert owner_cameras.status_code == 200, owner_cameras.text
        assert len(owner_cameras.json()) == 2
        assert admin_cameras.status_code == 200
        assert len(admin_cameras.json()) == 1
        assert owner_events.status_code == 200
        assert {item["detection_type"] for item in owner_events.json()["items"]} == {
            "owner-test-a",
            "owner-test-b",
        }
        assert owner_analytics.status_code == 200
        assert owner_analytics.json()["summary"]["total_detections"] == 2
        assert admin_analytics.status_code == 200
        assert admin_analytics.json()["summary"]["total_detections"] == 1
        assert admin_cannot_get_b_event.status_code == 404
        assert owner_reports.status_code == 200
        assert owner_reports.json()["total"] == 2
        assert admin_reports.status_code == 200
        assert admin_reports.json()["total"] == 1
        assert owner_can_get_b_report.status_code == 200
        assert admin_cannot_get_b_report.status_code == 404
        assert owner_can_export_b_report.status_code == 200
        assert owner_users.status_code == 200
        assert len(owner_users.json()) == 2
        assert admin_users.status_code == 200
        assert [user["username"] for user in admin_users.json()] == [
            "owner_access_a"
        ]
        assert created_officer.status_code == 200, created_officer.text
        assert admin_created_officer.status_code == 200
        assert created_camera.status_code == 200
        assert over_quota_camera.status_code == 403
        with Session(engine) as session:
            created = (
                session.query(Camera)
                .filter(Camera.camera_name == "Owner-created camera")
                .one()
            )
            assert str(created.customer_profile_id) == profile_b_id
            owner_officer = (
                session.query(User)
                .filter(User.username == "owner_created_officer")
                .one()
            )
            owner_officer_id = str(owner_officer.user_id)
            assert str(owner_officer.customer_profile_id) == profile_b_id
            admin_officer = (
                session.query(User)
                .filter(User.username == "admin_created_officer")
                .one()
            )
            assert str(admin_officer.customer_profile_id) == profile_a_id
        with TestClient(app) as client:
            admin_cannot_revoke_other_tenant_officer = client.delete(
                f"/users/{owner_officer_id}", headers=admin_headers
            )
            owner_can_revoke_officer = client.delete(
                f"/users/{owner_officer_id}", headers=owner_headers
            )
        assert admin_cannot_revoke_other_tenant_officer.status_code == 404
        assert owner_can_revoke_officer.status_code == 200
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_officer_requires_explicit_tenant_membership_and_pending_is_denied():
    engine, db = _session()
    try:
        admin_role = Role(role_name="Admin")
        officer_role = Role(role_name="Officer")
        db.add_all([admin_role, officer_role])
        db.flush()
        admin, profile = _admin(db, admin_role, "membership_admin")
        officer = User(
            full_name="Unmapped Officer",
            username="unmapped_officer",
            email="unmapped_officer@example.com",
            password_hash="test-hash",
            role=officer_role,
        )
        officer.customer_profile = CustomerProfile(
            workflow_status="PLATFORM_CUSTOMER",
            account_status="ACTIVE",
        )
        db.add(officer)
        db.commit()

        assert customer_profile_for_user(officer) is None
        officer.customer_profile_id = profile.customer_profile_id
        db.flush()
        db.expire(officer, ["customer_membership"])
        assert (
            customer_profile_for_user(officer).customer_profile_id
            == profile.customer_profile_id
        )

        pending = User(
            full_name="Pending Admin",
            username="pending_admin",
            email="pending_admin@example.com",
            password_hash="test-hash",
            role=admin_role,
            status="Pending",
        )
        pending.customer_profile = CustomerProfile(
            workflow_status="UNREAD",
            account_status="PENDING",
        )
        db.add(pending)
        db.commit()
        try:
            ensure_user_can_access_platform(pending)
        except HTTPException as exc:
            assert exc.status_code == 403
        else:
            raise AssertionError("Pending customer unexpectedly passed activation gate")

        pending_with_active_profile = User(
            full_name="Status mismatch",
            username="pending_with_active_profile",
            email="pending_with_active_profile@example.com",
            password_hash="test-hash",
            role=admin_role,
            status="Pending",
        )
        pending_with_active_profile.customer_profile = CustomerProfile(
            workflow_status="PLATFORM_CUSTOMER",
            account_status="ACTIVE",
        )
        db.add(pending_with_active_profile)
        db.commit()
        try:
            ensure_user_can_access_platform(pending_with_active_profile)
        except HTTPException as exc:
            assert exc.status_code == 403
        else:
            raise AssertionError(
                "Pending user with an active profile unexpectedly passed activation gate"
            )
    finally:
        db.close()
        engine.dispose()


def test_websocket_broadcast_only_reaches_matching_tenant():
    class FakeSocket:
        def __init__(self):
            self.messages = []

        async def accept(self):
            return None

        async def send_json(self, message):
            self.messages.append(message)

    async def run():
        socket_a = FakeSocket()
        socket_b = FakeSocket()
        try:
            await manager.connect(
                socket_a,
                user_id="admin-a",
                role="Admin",
                customer_profile_id="tenant-a",
            )
            await manager.connect(
                socket_b,
                user_id="admin-b",
                role="Admin",
                customer_profile_id="tenant-b",
            )
            await manager.broadcast(
                {"event": "ai_event", "data": {"camera_id": "camera-a"}},
                audience_customer_profile_id="tenant-a",
            )
            assert len(socket_a.messages) == 1
            assert socket_b.messages == []
        finally:
            manager.disconnect(socket_a)
            manager.disconnect(socket_b)

    asyncio.run(run())


def test_detection_records_accept_server_resolved_tenant():
    tenant_id = uuid4()
    detection = build_detection_record(
        camera_id=uuid4(),
        owner_id=uuid4(),
        detection_type="person",
        confidence=0.95,
        customer_profile_id=tenant_id,
    )
    assert detection.customer_profile_id == tenant_id
