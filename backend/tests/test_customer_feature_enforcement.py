import os
import sys
import uuid

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.api.v1 import ai as ai_api, cameras as cameras_api
from app.core.customer_features import (
    FEATURE_KEYS,
    enabled_customer_features,
    enforce_camera_quota,
    has_customer_feature,
    require_customer_feature,
)
from app.core.security import create_access_token
from app.database.session import Base, get_db
from app.models.models import (
    Camera,
    AIEvent,
    CustomerFeaturePermission,
    CustomerProfile,
    Role,
    User,
    UserSettings,
)
from app.repositories.settings_repository import SettingsRepository
from app.repositories.camera_repository import CameraRepository


def _create_user(db, role_name="Admin", profile=True, all_features=False):
    role = db.query(Role).filter(Role.role_name == role_name).first()
    if role is None:
        role = Role(role_name=role_name)
        db.add(role)
        db.flush()
    user = User(
        full_name="Feature Test User",
        username=f"feature_{uuid.uuid4().hex}",
        email=f"{uuid.uuid4().hex}@example.com",
        password_hash="not-used",
        role=role,
        status="Active",
        is_verified=True,
    )
    db.add(user)
    db.flush()
    customer_profile = None
    if profile:
        customer_profile = CustomerProfile(
            user_id=user.user_id,
            workflow_status="PLATFORM_CUSTOMER",
            account_status="ACTIVE",
            all_features=all_features,
            max_camera_count=1,
        )
        user.customer_profile = customer_profile
        db.add(customer_profile)
        db.flush()
        user.customer_profile_id = customer_profile.customer_profile_id
    return user, customer_profile


def test_feature_permissions_gate_camera_api_and_report_effective_features():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        user, profile = _create_user(db)
        permission = CustomerFeaturePermission(
            customer_profile_id=profile.customer_profile_id,
            feature_key="cameras",
            is_allowed=True,
        )
        db.add(permission)
        db.commit()
        user_id = str(user.user_id)

    app = FastAPI()
    app.include_router(cameras_api.router)

    def override_get_db():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    token = create_access_token({"user_id": user_id, "role": "Owner"})
    headers = {"Authorization": f"Bearer {token}"}

    try:
        with TestClient(app) as client:
            allowed = client.get("/cameras/", headers=headers)
            denied = client.post(
                f"/cameras/{uuid.uuid4()}/start",
                headers=headers,
            )

        assert allowed.status_code == 200
        assert denied.status_code == 404
        with Session(engine) as db:
            assert enabled_customer_features(db, user_id, "Officer") == [
                "cameras",
            ]
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_pending_customer_is_denied_before_feature_endpoint():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        user, profile = _create_user(db)
        profile.workflow_status = "UNREAD"
        profile.account_status = "PENDING"
        db.commit()
        user_id = str(user.user_id)

    app = FastAPI()
    app.include_router(cameras_api.router)

    def override_get_db():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    token = create_access_token({"user_id": user_id, "role": "Owner"})

    try:
        with TestClient(app) as client:
            response = client.get(
                "/cameras/",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == 403
        assert "awaiting activation" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_active_customers_get_all_features_despite_legacy_permission_rows():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        enabled_user, enabled_profile = _create_user(db, all_features=True)
        disabled_user, disabled_profile = _create_user(db)
        for key in FEATURE_KEYS:
            db.add_all(
                [
                    CustomerFeaturePermission(
                        customer_profile_id=enabled_profile.customer_profile_id,
                        feature_key=key,
                        is_allowed=True,
                    ),
                    CustomerFeaturePermission(
                        customer_profile_id=disabled_profile.customer_profile_id,
                        feature_key=key,
                        is_allowed=False,
                    ),
                ]
            )
        db.commit()
        enabled_user_id = str(enabled_user.user_id)
        disabled_user_id = str(disabled_user.user_id)

    app = FastAPI()

    def make_feature_endpoint(key):
        async def feature_endpoint(
            _current_user: dict = Depends(require_customer_feature(key)),
        ):
            return {"feature": key}

        return feature_endpoint

    for key in FEATURE_KEYS:
        app.add_api_route(
            f"/features/{key}", make_feature_endpoint(key)
        )

    def override_get_db():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    enabled_headers = {
        "Authorization": f"Bearer {create_access_token({'user_id': enabled_user_id})}"
    }
    disabled_headers = {
        "Authorization": f"Bearer {create_access_token({'user_id': disabled_user_id})}"
    }

    try:
        with TestClient(app) as client:
            for key in FEATURE_KEYS:
                allowed = client.get(
                    f"/features/{key}", headers=enabled_headers
                )
                denied = client.get(
                    f"/features/{key}", headers=disabled_headers
                )
                assert allowed.status_code == 200
                assert allowed.json()["feature"] == key
                assert denied.status_code == 403
        with Session(engine) as db:
            assert enabled_customer_features(db, disabled_user_id, "Admin") == []
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_camera_quota_counts_offline_cameras_and_unmapped_admin_is_denied():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        user, profile = _create_user(db)
        db.add(
            Camera(
                camera_name="Offline camera",
                location="Gate",
                stream_url="0",
                camera_type="USB",
                status="Offline",
                owner_id=user.user_id,
            )
        )
        db.commit()

        try:
            enforce_camera_quota(db, str(user.user_id))
        except Exception as exc:
            assert getattr(exc, "status_code", None) == 403
        else:
            raise AssertionError("A full quota must reject additional cameras")

        try:
            CameraRepository(db).add_camera(
                Camera(
                    camera_name="Repository bypass",
                    location="Gate",
                    stream_url="0",
                    camera_type="USB",
                    owner_id=user.user_id,
                )
            )
        except Exception as exc:
            assert getattr(exc, "status_code", None) == 403
        else:
            raise AssertionError("Repository camera creation must enforce quota")
        assert db.query(Camera).filter(Camera.owner_id == user.user_id).count() == 1

        admin, _ = _create_user(db, role_name="Admin", profile=False)
        db.commit()
        try:
            enforce_camera_quota(db, str(admin.user_id))
        except Exception as exc:
            assert getattr(exc, "status_code", None) == 403
        else:
            raise AssertionError("An Admin without a tenant must be denied")
        assert not has_customer_feature(db, str(admin.user_id), "Admin", "analytics")
        assert profile.max_camera_count == 1
    engine.dispose()


def test_camera_creation_rejects_at_quota_and_allows_when_capacity_is_available():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        user, profile = _create_user(db)
        db.add(
            CustomerFeaturePermission(
                customer_profile_id=profile.customer_profile_id,
                feature_key="cameras",
                is_allowed=True,
            )
        )
        profile.max_camera_count = 0
        db.commit()
        user_id = str(user.user_id)

    app = FastAPI()
    app.include_router(cameras_api.router)

    def override_get_db():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    token = create_access_token({"user_id": user_id, "role": "Owner"})
    headers = {"Authorization": f"Bearer {token}"}
    form = {
        "camera_name": "Quota camera",
        "location": "Gate",
        "camera_type": "USB",
    }

    try:
        with TestClient(app) as client:
            denied = client.post("/cameras/", data=form, headers=headers)
            assert denied.status_code == 403
            with Session(engine) as db:
                profile = (
                    db.query(CustomerProfile)
                    .filter(CustomerProfile.user_id == user_id)
                    .first()
                )
                profile.max_camera_count = 1
                db.commit()
            accepted = client.post("/cameras/", data=form, headers=headers)

        assert accepted.status_code == 200
        with Session(engine) as db:
            assert db.query(Camera).filter(Camera.owner_id == user_id).count() == 1
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_active_customer_can_read_and_manage_alerts_without_legacy_grants():
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(engine)

        with Session(engine) as db:
            user, profile = _create_user(db)
            db.add(
                CustomerFeaturePermission(
                    customer_profile_id=profile.customer_profile_id,
                    feature_key="analytics",
                    is_allowed=True,
                )
            )
            db.add(
                CustomerFeaturePermission(
                    customer_profile_id=profile.customer_profile_id,
                    feature_key="alerts",
                    is_allowed=True,
                )
            )
            db.add(
                CustomerFeaturePermission(
                    customer_profile_id=profile.customer_profile_id,
                    feature_key="cameras",
                    is_allowed=True,
                )
            )
            camera = Camera(
                camera_name="Analytics camera",
                location="Gate",
                stream_url="0",
                camera_type="USB",
                owner_id=user.user_id,
            )
            db.add(camera)
            db.flush()
            event = AIEvent(
                camera_id=camera.camera_id,
                detected_by=user.user_id,
                detection_type="person",
                severity="Low",
            )
            db.add(event)
            db.commit()
            user_id = str(user.user_id)
            event_id = str(event.event_id)
            camera_id = str(camera.camera_id)

        app = FastAPI()
        app.include_router(ai_api.router)

        def override_get_db():
            with Session(engine) as db:
                yield db

        app.dependency_overrides[get_db] = override_get_db
        headers = {
            "Authorization": f"Bearer {create_access_token({'user_id': user_id})}"
        }

        try:
            with TestClient(app) as client:
                events = client.get("/ai/events", headers=headers)
                detail = client.get(f"/ai/events/{event_id}", headers=headers)
                acknowledge = client.patch(
                    f"/ai/events/{event_id}/read", headers=headers
                )
                manual_event = client.post(
                    "/ai/events/manual",
                    params={
                        "camera_id": camera_id,
                        "detection_type": "manual",
                        "severity": "Low",
                    },
                    headers=headers,
                )

            assert events.status_code == 200
            assert events.json()["items"][0]["event_id"] == event_id
            assert detail.status_code == 200
            assert detail.json()["event_id"] == event_id
            assert acknowledge.status_code == 200
            assert manual_event.status_code == 200
        finally:
            app.dependency_overrides.clear()
            engine.dispose()


def test_failed_camera_commit_removes_uploaded_video(tmp_path, monkeypatch):
    engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    with Session(engine) as db:
            user, profile = _create_user(db)
            db.add(
                CustomerFeaturePermission(
                    customer_profile_id=profile.customer_profile_id,
                    feature_key="cameras",
                    is_allowed=True,
                )
            )
            db.commit()
            user_id = str(user.user_id)

    upload_dir = tmp_path / "videos"
    upload_dir.mkdir()
    monkeypatch.setattr(cameras_api, "UPLOAD_DIR", upload_dir)

    def fail_camera_creation(self, camera_data, owner_id=None):
            raise RuntimeError("simulated database failure")

    monkeypatch.setattr(CameraRepository, "add_camera", fail_camera_creation)
    app = FastAPI()
    app.include_router(cameras_api.router)

    def override_get_db():
            with Session(engine) as db:
                yield db

    app.dependency_overrides[get_db] = override_get_db
    headers = {
            "Authorization": f"Bearer {create_access_token({'user_id': user_id})}"
    }

    try:
            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.post(
                    "/cameras/",
                    data={
                        "camera_name": "Uploaded camera",
                        "location": "Gate",
                        "camera_type": "UPLOAD",
                    },
                    files={"video_file": ("test.mp4", b"video data", "video/mp4")},
                    headers=headers,
                )

            assert response.status_code == 500
            assert list(upload_dir.iterdir()) == []
    finally:
            app.dependency_overrides.clear()
            engine.dispose()


def test_settings_reset_preserves_existing_abandoned_bag_threshold():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        user, _ = _create_user(db)
        settings = UserSettings(
            owner_id=user.user_id,
            abandoned_bag_seconds=137,
            detection_confidence=0.73,
        )
        db.add(settings)
        db.commit()

        reset = SettingsRepository(db).reset_to_defaults(str(user.user_id))

        assert reset.abandoned_bag_seconds == 137
        assert reset.detection_confidence == 0.5
    engine.dispose()
