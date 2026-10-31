from datetime import datetime, timezone
import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.v1 import auth, owner, users
from app.core.security import create_access_token
from app.database.session import Base, get_db
from app.models.models import (
    Camera,
    CustomerFeaturePermission,
    CustomerProfile,
    Role,
    SystemSettings,
    User,
)


def _new_user(role, name, *, verified=True, created_at=None):
    user = User(
        full_name=name,
        username=name.lower().replace(" ", "_"),
        email=f"{name.lower().replace(' ', '_')}@example.com",
        password_hash=f"not-returned-{uuid.uuid4()}",
        phone=f"555-{uuid.uuid4().int % 10000000:07d}",
        organization=f"{name} Airport",
        role=role,
        status="Active",
        is_verified=verified,
        created_at=created_at,
    )
    return user


@pytest.fixture
def owner_api():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        owner_role = Role(role_name="Owner")
        admin_role = Role(role_name="Admin")
        officer_role = Role(role_name="Officer")
        db.add_all([owner_role, admin_role, officer_role])
        db.flush()

        owner_user = _new_user(owner_role, "System Owner")
        admin = _new_user(admin_role, "Legacy Admin")
        officer = _new_user(officer_role, "Platform Officer")
        unread_old = _new_user(
            officer_role,
            "Unread Oldest",
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        unread_old.status = "Pending"
        unread_new = _new_user(
            officer_role,
            "Unread Newer",
            created_at=datetime(2024, 2, 1, tzinfo=timezone.utc),
        )
        unverified = _new_user(officer_role, "Unverified Request", verified=False)
        under_review = _new_user(officer_role, "Review Customer")
        platform_admin = _new_user(admin_role, "Legacy Platform Admin")
        inactive_admin = _new_user(admin_role, "Inactive Platform Admin")
        no_quota = _new_user(officer_role, "Missing Quota")
        no_features = _new_user(officer_role, "Missing Features")
        unverified_review = _new_user(
            officer_role, "Unverified Review", verified=False
        )

        profiles = {
            "unread_old": CustomerProfile(
                user=unread_old,
                workflow_status="UNREAD",
                account_status="PENDING",
                activation_date=datetime(2024, 6, 7, tzinfo=timezone.utc),
            ),
            "unread_new": CustomerProfile(
                user=unread_new, workflow_status="UNREAD", account_status="PENDING"
            ),
            "unverified": CustomerProfile(
                user=unverified,
                workflow_status="UNREAD",
                account_status="PENDING",
            ),
            "under_review": CustomerProfile(
                user=under_review,
                workflow_status="UNDER_REVIEW",
                account_status="PENDING",
            ),
            "platform_admin": CustomerProfile(
                user=platform_admin,
                workflow_status="PLATFORM_CUSTOMER",
                account_status="ACTIVE",
                all_features=True,
                max_camera_count=None,
                owner_notes="Private legacy note",
            ),
            "inactive_admin": CustomerProfile(
                user=inactive_admin,
                workflow_status="PLATFORM_CUSTOMER",
                account_status="INACTIVE",
                all_features=True,
                max_camera_count=4,
                owner_notes="Retain after state changes",
            ),
            "no_quota": CustomerProfile(
                user=no_quota, workflow_status="UNREAD", account_status="PENDING"
            ),
            "no_features": CustomerProfile(
                user=no_features,
                workflow_status="UNDER_REVIEW",
                account_status="PENDING",
                max_camera_count=3,
            ),
            "unverified_review": CustomerProfile(
                user=unverified_review,
                workflow_status="UNDER_REVIEW",
                account_status="PENDING",
            ),
        }
        db.add_all(
            [
                owner_user,
                admin,
                officer,
                unread_old,
                unread_new,
                unverified,
                under_review,
                platform_admin,
                inactive_admin,
                no_quota,
                no_features,
                unverified_review,
                *profiles.values(),
            ]
        )
        db.add(
            SystemSettings(
                abandoned_bag_enabled=False,
                loitering_enabled=False,
            )
        )
        db.flush()
        profiles["platform_admin"].feature_permissions.append(
            CustomerFeaturePermission(
                feature_key="cameras", is_allowed=True
            )
        )
        profiles["inactive_admin"].feature_permissions.append(
            CustomerFeaturePermission(
                feature_key="analytics", is_allowed=True
            )
        )
        owned_camera = Camera(
            camera_name="Legacy camera",
            location="Gate A",
            stream_url="rtsp://example/stream",
            camera_type="LIVE",
            owner_id=platform_admin.user_id,
        )
        db.add(owned_camera)
        db.commit()

        ids = {
            key: str(profile.customer_profile_id)
            for key, profile in profiles.items()
        }
        user_ids = {
            "owner": str(owner_user.user_id),
            "admin": str(admin.user_id),
            "officer": str(officer.user_id),
            "unread_old": str(unread_old.user_id),
            "unread_new": str(unread_new.user_id),
            "no_quota": str(no_quota.user_id),
            "no_features": str(no_features.user_id),
            "platform_admin": str(platform_admin.user_id),
            "inactive_admin": str(inactive_admin.user_id),
            "camera": str(owned_camera.camera_id),
            "camera_owner": str(owned_camera.owner_id),
        }

    app = FastAPI()
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(users.router, prefix="/api/v1")
    app.include_router(owner.router, prefix="/api/v1")

    def override_get_db():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db

    def headers(user_id):
        token = create_access_token(
            {"user_id": user_id, "role": "Owner"}
        )
        return {"Authorization": f"Bearer {token}"}

    with TestClient(app) as client:
        yield {
            "client": client,
            "headers": headers,
            "ids": ids,
            "user_ids": user_ids,
            "engine": engine,
        }
    app.dependency_overrides.clear()
    engine.dispose()


def _owner_headers(api):
    return api["headers"](api["user_ids"]["owner"])


def test_owner_lists_workflow_sections_and_filters_unverified_requests(owner_api):
    api = owner_api
    headers = _owner_headers(api)

    unread = api["client"].get("/api/v1/owner/requests/unread", headers=headers)
    assert unread.status_code == 200
    unread_items = unread.json()["items"]
    unread_ids = [item["customer_profile_id"] for item in unread_items]
    assert unread_ids[:2] == [
        api["ids"]["unread_old"],
        api["ids"]["unread_new"],
    ]
    assert set(unread_ids) == {
        api["ids"]["unread_old"],
        api["ids"]["unread_new"],
        api["ids"]["no_quota"],
    }

    review = api["client"].get(
        "/api/v1/owner/requests/under-review", headers=headers
    )
    assert {item["customer_profile_id"] for item in review.json()["items"]} == {
        api["ids"]["under_review"],
        api["ids"]["no_features"],
        api["ids"]["unverified_review"],
    }

    customers = api["client"].get("/api/v1/owner/customers", headers=headers)
    assert {item["customer_profile_id"] for item in customers.json()["items"]} == {
        api["ids"]["platform_admin"],
        api["ids"]["inactive_admin"],
    }
    assert customers.json()["total"] == 2


@pytest.mark.parametrize("role_key", ["admin", "officer"])
def test_non_owner_roles_are_forbidden_even_with_forged_jwt_role(owner_api, role_key):
    response = owner_api["client"].get(
        "/api/v1/owner/requests/unread",
        headers=owner_api["headers"](owner_api["user_ids"][role_key]),
    )
    assert response.status_code == 403


def test_owner_endpoints_require_authentication(owner_api):
    response = owner_api["client"].get("/api/v1/owner/customers")
    assert response.status_code == 401


def test_owner_search_and_details_use_stable_profile_identity(owner_api):
    api = owner_api
    headers = _owner_headers(api)
    by_name = api["client"].get(
        "/api/v1/owner/requests/under-review",
        params={"search": "review customer"},
        headers=headers,
    )
    assert [item["customer_profile_id"] for item in by_name.json()["items"]] == [
        api["ids"]["under_review"]
    ]

    with Session(api["engine"]) as db:
        profile = db.get(CustomerProfile, api["ids"]["under_review"])
        phone = profile.user.phone
    by_phone = api["client"].get(
        "/api/v1/owner/requests/under-review",
        params={"search": phone[-4:]},
        headers=headers,
    )
    assert [item["customer_profile_id"] for item in by_phone.json()["items"]] == [
        api["ids"]["under_review"]
    ]

    details = api["client"].get(
        f"/api/v1/owner/customers/{api['ids']['platform_admin']}",
        headers=headers,
    )
    assert details.status_code == 200
    body = details.json()
    assert body["customer_profile_id"] == api["ids"]["platform_admin"]
    assert body["user_id"] == api["user_ids"]["platform_admin"]
    assert body["password"] == owner.MASKED_PASSWORD
    assert "password_hash" not in body
    assert body["owner_notes"] == "Private legacy note"


def test_customer_auth_and_profile_responses_never_expose_owner_notes(owner_api):
    api = owner_api
    headers = api["headers"](api["user_ids"]["platform_admin"])
    auth_state = api["client"].get("/api/v1/auth/me", headers=headers)
    profile = api["client"].get("/api/v1/users/profile", headers=headers)
    assert auth_state.status_code == 200
    assert profile.status_code == 200
    assert "owner_notes" not in auth_state.json()
    assert "owner_notes" not in profile.json()
    assert "password_hash" not in profile.json()


def test_save_configuration_does_not_change_customer_state(owner_api):
    api = owner_api
    profile_id = api["ids"]["under_review"]
    response = api["client"].patch(
        f"/api/v1/owner/customers/{profile_id}/configuration",
        headers=_owner_headers(api),
        json={
            "max_camera_count": 0,
            "owner_notes": "Review configuration",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["max_camera_count"] == 0
    assert body["workflow_status"] == "UNDER_REVIEW"
    assert body["account_status"] == "PENDING"
    assert body["owner_notes"] == "Review configuration"
    assert "all_features" not in body
    assert "feature_keys" not in body
    assert "activation_date" not in body

    invalid = api["client"].patch(
        f"/api/v1/owner/customers/{profile_id}/configuration",
        headers=_owner_headers(api),
        json={
            "max_camera_count": -1,
            "owner_notes": None,
        },
    )
    assert invalid.status_code == 422


def test_configuration_rejects_obsolete_feature_and_date_inputs(owner_api):
    api = owner_api
    response = api["client"].patch(
        f"/api/v1/owner/customers/{api['ids']['under_review']}/configuration",
        headers=_owner_headers(api),
        json={
            "max_camera_count": None,
            "all_features": True,
            "feature_keys": [],
        },
    )
    assert response.status_code == 422


def test_activation_requires_configured_camera_quota(owner_api):
    api = owner_api
    profile_id = api["ids"]["no_quota"]
    response = api["client"].post(
        f"/api/v1/owner/customers/{profile_id}/activate",
        headers=_owner_headers(api),
    )
    assert response.status_code == 422
    details = api["client"].get(
        f"/api/v1/owner/customers/{profile_id}", headers=_owner_headers(api)
    )
    assert details.json()["account_status"] == "PENDING"


def test_activation_saves_quota_and_grants_all_features_without_date_or_permissions(
    owner_api,
):
    api = owner_api
    profile_id = api["ids"]["unread_old"]
    headers = _owner_headers(api)
    review = api["client"].post(
        f"/api/v1/owner/customers/{profile_id}/under-review", headers=headers
    )
    assert review.status_code == 200
    unread = api["client"].get("/api/v1/owner/requests/unread", headers=headers)
    assert profile_id not in {
        item["customer_profile_id"] for item in unread.json()["items"]
    }
    review_list = api["client"].get(
        "/api/v1/owner/requests/under-review", headers=headers
    )
    assert profile_id in {
        item["customer_profile_id"] for item in review_list.json()["items"]
    }
    activated = api["client"].post(
        f"/api/v1/owner/customers/{profile_id}/activate",
        headers=headers,
        json={"max_camera_count": 5},
    )
    assert activated.status_code == 200
    assert activated.json()["workflow_status"] == "PLATFORM_CUSTOMER"
    assert activated.json()["account_status"] == "ACTIVE"
    assert activated.json()["max_camera_count"] == 5
    assert "activation_date" not in activated.json()

    with Session(api["engine"]) as db:
        profile = db.get(CustomerProfile, uuid.UUID(profile_id))
        activated_user = db.get(User, api["user_ids"]["unread_old"])
        assert activated_user.status == "Active"
        assert profile.all_features is True
        assert profile.activation_date.date() == datetime(2024, 6, 7).date()
        assert db.query(CustomerFeaturePermission).filter(
            CustomerFeaturePermission.customer_profile_id == profile.customer_profile_id
        ).count() == 0
        settings = db.query(SystemSettings).one()
        assert settings.abandoned_bag_enabled is False
        assert settings.loitering_enabled is False

    platform = api["client"].get("/api/v1/owner/customers", headers=headers)
    assert profile_id in {
        item["customer_profile_id"] for item in platform.json()["items"]
    }


def test_activation_accepts_zero_quota_and_rejects_unverified_customer(owner_api):
    api = owner_api
    headers = _owner_headers(api)
    profile_id = api["ids"]["unverified"]
    rejected = api["client"].post(
        f"/api/v1/owner/customers/{profile_id}/activate",
        headers=headers,
        json={"max_camera_count": 2},
    )
    assert rejected.status_code == 422
    assert rejected.json()["detail"] == "Customer email is not verified"

    profile_id = api["ids"]["no_features"]
    activated = api["client"].post(
        f"/api/v1/owner/customers/{profile_id}/activate",
        headers=headers,
        json={"max_camera_count": 0},
    )
    assert activated.status_code == 200
    assert activated.json()["max_camera_count"] == 0
    with Session(api["engine"]) as db:
        profile = db.get(CustomerProfile, uuid.UUID(profile_id))
        assert profile.all_features is True
        assert profile.activation_date is None


def test_deactivate_and_reactivate_preserve_configuration_and_customer_data(owner_api):
    api = owner_api
    profile_id = api["ids"]["inactive_admin"]
    headers = _owner_headers(api)

    reactivated = api["client"].post(
        f"/api/v1/owner/customers/{profile_id}/reactivate", headers=headers
    )
    assert reactivated.status_code == 200
    assert reactivated.json()["account_status"] == "ACTIVE"
    assert reactivated.json()["max_camera_count"] == 4
    assert reactivated.json()["owner_notes"] == "Retain after state changes"
    with Session(api["engine"]) as db:
        assert db.get(User, api["user_ids"]["inactive_admin"]).status == "Active"

    deactivated = api["client"].post(
        f"/api/v1/owner/customers/{profile_id}/deactivate", headers=headers
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["workflow_status"] == "PLATFORM_CUSTOMER"
    assert deactivated.json()["account_status"] == "INACTIVE"
    assert deactivated.json()["max_camera_count"] == 4
    assert deactivated.json()["owner_notes"] == "Retain after state changes"
    platform = api["client"].get("/api/v1/owner/customers", headers=headers)
    assert profile_id in {
        item["customer_profile_id"] for item in platform.json()["items"]
    }

    with Session(api["engine"]) as db:
        user = db.get(User, api["user_ids"]["inactive_admin"])
        camera = db.get(Camera, api["user_ids"]["camera"])
        assert user.role.role_name == "Admin"
        assert camera.owner_id == uuid.UUID(api["user_ids"]["camera_owner"])
        profile = db.get(CustomerProfile, uuid.UUID(profile_id))
        assert user.status == "Inactive"
        assert profile.all_features is True
        assert db.query(CustomerFeaturePermission).filter(
            CustomerFeaturePermission.customer_profile_id == profile.customer_profile_id,
            CustomerFeaturePermission.feature_key == "analytics",
            CustomerFeaturePermission.is_allowed.is_(True),
        ).count() == 1


def test_invalid_transitions_and_unknown_profiles_are_rejected(owner_api):
    api = owner_api
    headers = _owner_headers(api)
    reactivate_active = api["client"].post(
        f"/api/v1/owner/customers/{api['ids']['platform_admin']}/reactivate",
        headers=headers,
    )
    assert reactivate_active.status_code == 409
    already_active = api["client"].post(
        f"/api/v1/owner/customers/{api['ids']['platform_admin']}/deactivate",
        headers=headers,
    )
    assert already_active.status_code == 200
    repeated = api["client"].post(
        f"/api/v1/owner/customers/{api['ids']['platform_admin']}/deactivate",
        headers=headers,
    )
    assert repeated.status_code == 409
    reactivated = api["client"].post(
        f"/api/v1/owner/customers/{api['ids']['platform_admin']}/reactivate",
        headers=headers,
    )
    assert reactivated.status_code == 200
    repeated_reactivation = api["client"].post(
        f"/api/v1/owner/customers/{api['ids']['platform_admin']}/reactivate",
        headers=headers,
    )
    assert repeated_reactivation.status_code == 409
    move_platform_to_review = api["client"].post(
        f"/api/v1/owner/customers/{api['ids']['platform_admin']}/under-review",
        headers=headers,
    )
    assert move_platform_to_review.status_code == 409
    missing = api["client"].get(
        f"/api/v1/owner/customers/{uuid.uuid4()}", headers=headers
    )
    assert missing.status_code == 404


def test_owner_feature_registry_only_contains_existing_customer_sections(owner_api):
    response = owner_api["client"].get(
        "/api/v1/owner/features", headers=_owner_headers(owner_api)
    )
    assert response.status_code == 200
    assert {feature["feature_key"] for feature in response.json()} == {
        "dashboard",
        "cameras",
        "analytics",
        "alerts",
        "profile",
        "settings",
    }
