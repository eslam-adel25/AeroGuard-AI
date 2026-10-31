from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.v1 import uploads, users
from app.core.security import create_access_token
from app.database.session import Base, get_db
from app.models.models import (
    AIEvent,
    Camera,
    CustomerFeaturePermission,
    CustomerProfile,
    Role,
    User,
)


def _create_user(db, role, username, *, workflow="PLATFORM_CUSTOMER", status="ACTIVE"):
    user = User(
        full_name=username,
        username=username,
        email=f"{username}@example.com",
        password_hash="test-hash",
        role=role,
        status="Active",
        is_verified=True,
    )
    if role.role_name != "Owner":
        user.customer_profile = CustomerProfile(
            workflow_status=workflow,
            account_status=status,
            all_features=True,
        )
    db.add(user)
    db.flush()
    if user.customer_profile is not None:
        user.customer_profile_id = user.customer_profile.customer_profile_id
    return user


def _headers(user_id: str):
    token = create_access_token(
        {"user_id": user_id, "role": "forged-role"}
    )
    return {"Authorization": f"Bearer {token}"}


def test_uploads_require_record_ownership_and_preserve_profile_avatar(
    tmp_path, monkeypatch
):
    root = tmp_path / "uploads"
    avatar_dir = root / "avatars"
    screenshot_dir = root / "ai_events"
    video_dir = root / "videos"
    report_dir = root / "reports"
    for folder in (avatar_dir, screenshot_dir, video_dir, report_dir):
        folder.mkdir(parents=True)

    customer_avatar = avatar_dir / "customer.png"
    other_avatar = avatar_dir / "other.png"
    owner_avatar = avatar_dir / "owner.png"
    own_screenshot = screenshot_dir / "own.jpg"
    other_screenshot = screenshot_dir / "other.jpg"
    analytics_screenshot = screenshot_dir / "analytics.jpg"
    own_video = video_dir / "own.mp4"
    other_video = video_dir / "other.mp4"
    report_pdf = report_dir / "legacy-report.pdf"
    for path in (
        customer_avatar,
        other_avatar,
        owner_avatar,
        own_screenshot,
        other_screenshot,
        analytics_screenshot,
        own_video,
        other_video,
        report_pdf,
    ):
        path.write_bytes(path.name.encode())
    monkeypatch.setattr(uploads, "UPLOAD_ROOT", root)

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        officer = Role(role_name="Officer")
        owner_role = Role(role_name="Owner")
        admin_role = Role(role_name="Admin")
        db.add_all([officer, owner_role, admin_role])
        db.flush()

        customer = _create_user(db, admin_role, "customer")
        other_customer = _create_user(db, admin_role, "other_customer")
        owner = _create_user(db, owner_role, "owner")
        admin = _create_user(db, admin_role, "legacy_admin")
        pending = _create_user(
            db, admin_role, "pending", workflow="UNREAD", status="PENDING"
        )
        analytics_only = _create_user(db, admin_role, "analytics_only")
        analytics_only.customer_profile.all_features = False
        no_analytics_or_alerts = _create_user(db, admin_role, "no_event_features")
        no_analytics_or_alerts.customer_profile.all_features = False
        db.add(
            CustomerFeaturePermission(
                customer_profile_id=analytics_only.customer_profile.customer_profile_id,
                feature_key="analytics",
                is_allowed=True,
            )
        )
        inactive = _create_user(
            db,
            admin_role,
            "inactive",
            workflow="PLATFORM_CUSTOMER",
            status="INACTIVE",
        )
        customer.profile_picture = "/uploads/avatars/customer.png"
        other_customer.profile_picture = "/uploads/avatars/other.png"
        owner.profile_picture = "/uploads/avatars/owner.png"

        own_camera = Camera(
            camera_name="Customer camera",
            location="Customer site",
            stream_url=str(own_video),
            camera_type="UPLOAD",
            owner_id=customer.user_id,
        )
        other_camera = Camera(
            camera_name="Other camera",
            location="Other site",
            stream_url=str(other_video),
            camera_type="UPLOAD",
            owner_id=other_customer.user_id,
        )
        analytics_camera = Camera(
            camera_name="Analytics camera",
            location="Analytics site",
            stream_url=str(video_dir / "analytics.mp4"),
            camera_type="UPLOAD",
            owner_id=analytics_only.user_id,
        )
        db.add_all([own_camera, other_camera, analytics_camera])
        db.flush()
        db.add_all(
            [
                AIEvent(
                    camera_id=own_camera.camera_id,
                    detection_type="test",
                    severity="Low",
                    screenshot_path=str(own_screenshot),
                ),
                AIEvent(
                    camera_id=other_camera.camera_id,
                    detection_type="test",
                    severity="Low",
                    screenshot_path=str(other_screenshot),
                ),
                AIEvent(
                    camera_id=analytics_camera.camera_id,
                    detection_type="analytics test",
                    severity="Low",
                    screenshot_path=str(analytics_screenshot),
                ),
            ]
        )
        db.commit()
        identities = {
            "customer": str(customer.user_id),
            "other_customer": str(other_customer.user_id),
            "owner": str(owner.user_id),
            "admin": str(admin.user_id),
            "pending": str(pending.user_id),
            "analytics_only": str(analytics_only.user_id),
            "no_event_features": str(no_analytics_or_alerts.user_id),
            "inactive": str(inactive.user_id),
        }

    app = FastAPI()
    app.include_router(users.router, prefix="/api/v1")
    app.include_router(uploads.router)

    def override_get_db():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            customer_headers = _headers(identities["customer"])

            own_image = client.get(
                "/uploads/avatars/customer.png", headers=customer_headers
            )
            assert own_image.status_code == 200
            assert own_image.content == customer_avatar.read_bytes()
            assert own_image.headers["cache-control"] == "private, no-store"

            own_avatar_api = client.get(
                "/api/v1/users/profile/avatar", headers=customer_headers
            )
            assert own_avatar_api.status_code == 200
            assert own_avatar_api.content == customer_avatar.read_bytes()

            assert client.get(
                "/uploads/ai_events/own.jpg", headers=customer_headers
            ).status_code == 200
            assert client.get(
                "/uploads/ai_events/analytics.jpg",
                headers=_headers(identities["analytics_only"]),
            ).status_code == 200
            assert client.get(
                "/uploads/ai_events/analytics.jpg",
                headers=_headers(identities["no_event_features"]),
            ).status_code == 403
            assert client.get(
                "/uploads/videos/own.mp4", headers=customer_headers
            ).status_code == 200

            assert client.get(
                "/uploads/avatars/other.png", headers=customer_headers
            ).status_code == 403
            assert client.get(
                "/uploads/ai_events/other.jpg", headers=customer_headers
            ).status_code == 404
            assert client.get(
                "/uploads/videos/other.mp4", headers=customer_headers
            ).status_code == 404

            assert client.get(
                "/uploads/ai_events/own.jpg",
                headers=_headers(identities["pending"]),
            ).status_code == 403
            assert client.get(
                "/api/v1/users/profile/avatar",
                headers=_headers(identities["pending"]),
            ).status_code == 403
            assert client.get(
                "/uploads/avatars/customer.png",
                headers=_headers(identities["inactive"]),
            ).status_code == 403
            assert client.get(
                "/api/v1/users/profile/avatar",
                headers=_headers(identities["inactive"]),
            ).status_code == 403

            owner_headers = _headers(identities["owner"])
            owner_image = client.get(
                "/uploads/avatars/owner.png", headers=owner_headers
            )
            assert owner_image.status_code == 200
            assert owner_image.content == owner_avatar.read_bytes()
            owner_profile_image = client.get(
                "/api/v1/users/profile/avatar", headers=owner_headers
            )
            assert owner_profile_image.status_code == 200
            assert owner_profile_image.content == owner_avatar.read_bytes()
            owner_customer_avatar = client.get(
                "/uploads/avatars/customer.png", headers=owner_headers
            )
            assert owner_customer_avatar.status_code == 200
            assert owner_customer_avatar.content == customer_avatar.read_bytes()
            assert client.get(
                "/uploads/avatars/owner.png",
                headers=_headers(identities["admin"]),
            ).status_code == 403
            assert client.get(
                "/uploads/ai_events/own.jpg", headers=owner_headers
            ).status_code == 200

            assert client.get(
                "/uploads/reports/legacy-report.pdf",
                headers=customer_headers,
            ).status_code == 404
            assert client.get("/uploads/ai_events/own.jpg").status_code == 401
            assert client.get(
                "/uploads/../../README.md", headers=customer_headers
            ).status_code == 404

            admin_image = client.get(
                "/uploads/avatars/customer.png",
                headers=_headers(identities["admin"]),
            )
            assert admin_image.status_code == 403
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
