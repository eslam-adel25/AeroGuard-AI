import pytest
from datetime import datetime, timedelta
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.v1 import auth, uploads, users
from app.core.auth_middleware import get_current_user, role_required
from app.core.security import create_access_token, hash_password, verify_password
from app.database.session import Base, get_db
from app.models.models import CustomerProfile, RefreshToken, Role, User


@pytest.fixture
def auth_client(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Role(role_name="Officer"))
        db.commit()

    app = FastAPI()
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(users.router, prefix="/api/v1")

    @app.get("/protected")
    async def protected(current_user: dict = Depends(get_current_user)):
        return current_user

    @app.get("/admin-protected")
    async def admin_protected(
        current_user: dict = Depends(role_required(["Administrator"])),
    ):
        return current_user

    def override_get_db():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    auth._AUTH_ATTEMPT_HISTORY.clear()
    monkeypatch.setenv("REQUIRE_EMAIL_VERIFICATION", "true")
    with TestClient(app) as client:
        yield client, engine
    auth._AUTH_ATTEMPT_HISTORY.clear()
    app.dependency_overrides.clear()
    engine.dispose()


def test_registration_verification_stays_pending_until_activation(
    auth_client, monkeypatch
):
    client, engine = auth_client
    with Session(engine) as db:
        admin_role = Role(role_name="Admin")
        owner_role = Role(role_name="Owner")
        officer_role = db.query(Role).filter(Role.role_name == "Officer").one()
        db.add_all([admin_role, owner_role])
        db.flush()
        admin_role_id = admin_role.role_id
        existing_users = [
            User(
                full_name="Existing Admin",
                username="existing_admin",
                email="existing_admin@example.com",
                password_hash="not-used",
                role_id=admin_role.role_id,
                status="Active",
                is_verified=True,
            ),
            User(
                full_name="Existing Officer",
                username="existing_officer",
                email="existing_officer@example.com",
                password_hash="not-used",
                role_id=officer_role.role_id,
                status="Active",
                is_verified=True,
            ),
            User(
                full_name="Existing Owner",
                username="existing_owner",
                email="existing_owner@example.com",
                password_hash="not-used",
                role_id=owner_role.role_id,
                status="Active",
                is_verified=True,
            ),
            User(
                full_name="Existing Pending",
                username="existing_pending",
                email="existing_pending@example.com",
                password_hash="not-used",
                role_id=officer_role.role_id,
                status="Pending",
                is_verified=True,
            ),
        ]
        db.add_all(existing_users)
        db.flush()
        existing_users[-1].customer_profile = CustomerProfile(
            workflow_status="UNREAD",
            account_status="PENDING",
        )
        db.commit()
        existing_user_ids = {
            user.username: str(user.user_id) for user in existing_users
        }

    sent = {}
    monkeypatch.setattr(
        auth,
        "send_verification_email",
        lambda email, full_name, token, otp: sent.update(
            email=email, token=token, otp=otp
        ),
    )
    registration = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Pending Customer",
            "username": "pending_customer",
            "email": "pending@example.com",
            "password": "StrongPass123!",
            "phone": "555-0100",
        },
    )
    assert registration.status_code == 201
    assert registration.json()["requires_verification"] is True
    assert client.post(
        "/api/v1/auth/login",
        json={"username": "pending_customer", "password": "StrongPass123!"},
    ).status_code == 403

    verified = client.post(
        "/api/v1/auth/verify-otp",
        json={"email": sent["email"], "code": sent["otp"]},
    )
    assert verified.status_code == 200

    login = client.post(
        "/api/v1/auth/login",
        json={"username": "pending_customer", "password": "StrongPass123!"},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    identity = client.get("/api/v1/auth/me", headers=headers)
    assert identity.status_code == 200
    assert identity.json()["account_status"] == "PENDING"
    assert identity.json()["workflow_status"] == "UNREAD"
    assert client.get("/protected", headers=headers).status_code == 403
    refreshed_pending = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": login.json()["refresh_token"]},
    )
    assert refreshed_pending.status_code == 200
    assert client.get(
        "/protected",
        headers={
            "Authorization": f"Bearer {refreshed_pending.json()['access_token']}"
        },
    ).status_code == 403

    with Session(engine) as db:
        user = db.query(User).filter(User.username == "pending_customer").one()
        profile = (
            db.query(CustomerProfile)
            .filter(CustomerProfile.user_id == user.user_id)
            .one()
        )
        assert profile.account_status == "PENDING"
        assert profile.workflow_status == "UNREAD"
        assert user.status == "Pending"
        assert user.role.role_name == "Admin"
        assert user.role_id == admin_role_id
        profile.workflow_status = "PLATFORM_CUSTOMER"
        profile.account_status = "ACTIVE"
        profile.all_features = True
        user.status = "Active"
        db.commit()

    active_response = client.get("/protected", headers=headers)
    assert active_response.status_code == 200
    assert active_response.json()["account_status"] == "ACTIVE"
    assert {
        "dashboard",
        "cameras",
        "analytics",
        "alerts",
        "profile",
        "settings",
    }.issubset(set(client.get("/api/v1/auth/me", headers=headers).json()["enabled_features"]))
    assert client.get("/admin-protected", headers=headers).status_code == 200
    for username, expected_status in (
        ("existing_admin", 200),
        ("existing_officer", 403),
        ("existing_owner", 403),
        ("existing_pending", 403),
    ):
        existing_token = create_access_token(
            {"user_id": existing_user_ids[username]}
        )
        assert client.get(
            "/admin-protected",
            headers={"Authorization": f"Bearer {existing_token}"},
        ).status_code == expected_status

    with Session(engine) as db:
        user = db.query(User).filter(User.username == "pending_customer").one()
        profile = (
            db.query(CustomerProfile)
            .filter(CustomerProfile.user_id == user.user_id)
            .one()
        )
        assert user.status == "Active"
        assert user.role.role_name == "Admin"
        for username, role_name, status_value in (
            ("existing_admin", "Admin", "Active"),
            ("existing_officer", "Officer", "Active"),
            ("existing_owner", "Owner", "Active"),
            ("existing_pending", "Officer", "Pending"),
        ):
            existing_user = (
                db.query(User).filter(User.username == username).one()
            )
            assert existing_user.role.role_name == role_name
            assert existing_user.status == status_value
        existing_pending = (
            db.query(User)
            .filter(User.username == "existing_pending")
            .one()
        )
        assert existing_pending.customer_profile.account_status == "PENDING"
        profile.account_status = "INACTIVE"
        db.commit()

    assert client.get("/protected", headers=headers).status_code == 403
    assert client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": login.json()["refresh_token"]},
    ).status_code == 403


def test_identity_and_access_come_from_database_not_jwt_role(auth_client):
    client, engine = auth_client
    with Session(engine) as db:
        admin_role = Role(role_name="Admin")
        db.add(admin_role)
        db.flush()
        user = User(
            full_name="Legacy Admin",
            username="legacy_admin",
            email="admin@example.com",
            password_hash="not-used",
            role_id=admin_role.role_id,
            status="Active",
            is_verified=True,
        )
        user.customer_profile = CustomerProfile(
            workflow_status="PLATFORM_CUSTOMER",
            account_status="ACTIVE",
            all_features=True,
        )
        db.add(user)
        db.flush()
        user.customer_profile_id = user.customer_profile.customer_profile_id
        db.commit()
        user_id = str(user.user_id)

    token = create_access_token(
        {"user_id": user_id, "username": "legacy_admin", "role": "Officer"}
    )
    response = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["role"] == "Admin"
    assert response.json()["user_id"] == user_id

    with Session(engine) as db:
        owner_role = Role(role_name="Owner")
        db.add(owner_role)
        db.flush()
        owner = User(
            full_name="Owner",
            username="owner",
            email="owner@example.com",
            password_hash="not-used",
            role_id=owner_role.role_id,
            status="Active",
            is_verified=True,
        )
        db.add(owner)
        db.commit()
        owner_id = str(owner.user_id)

    owner_token = create_access_token(
        {"user_id": owner_id, "role": "Administrator"}
    )
    assert client.get(
        "/protected", headers={"Authorization": f"Bearer {owner_token}"}
    ).status_code == 403
    owner_identity = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert owner_identity.status_code == 200
    assert owner_identity.json()["is_owner"] is True

    admin_headers = {"Authorization": f"Bearer {token}"}
    listed_users = client.get("/api/v1/users/", headers=admin_headers)
    assert listed_users.status_code == 200
    assert [row["username"] for row in listed_users.json()] == ["legacy_admin"]
    role_names = {
        row["role_name"]
        for row in client.get("/api/v1/users/roles").json()
    }
    assert "Owner" not in role_names


def test_active_legacy_customer_is_not_reasked_to_verify_email(auth_client):
    client, engine = auth_client
    with Session(engine) as db:
        role = db.query(Role).filter(Role.role_name == "Officer").one()
        user = User(
            full_name="Legacy Customer",
            username="legacy_customer",
            email="legacy@example.com",
            password_hash=auth.hash_password("StrongPass123!"),
            role_id=role.role_id,
            status="Active",
            is_verified=False,
        )
        user.customer_profile = CustomerProfile(
            workflow_status="PLATFORM_CUSTOMER",
            account_status="ACTIVE",
            all_features=True,
        )
        db.add(user)
        db.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={"username": "legacy_customer", "password": "StrongPass123!"},
    )
    assert response.status_code == 200


def test_registration_without_email_verification_still_requires_activation(
    auth_client, monkeypatch
):
    client, engine = auth_client
    monkeypatch.setenv("REQUIRE_EMAIL_VERIFICATION", "false")
    registration = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Unverified Customer",
            "username": "unverified_customer",
            "email": "unverified@example.com",
            "password": "StrongPass123!",
            "phone": "555-0101",
        },
    )
    assert registration.status_code == 201
    assert registration.json()["requires_verification"] is False

    login = client.post(
        "/api/v1/auth/login",
        json={
            "username": "unverified_customer",
            "password": "StrongPass123!",
        },
    )
    assert login.status_code == 200


def test_owner_can_manage_only_own_profile_and_account_security(
    auth_client, tmp_path, monkeypatch
):
    client, engine = auth_client
    with Session(engine) as db:
        owner_role = Role(role_name="Owner")
        db.add(owner_role)
        db.flush()
        owner = User(
            full_name="Owner Account",
            username="owner_account",
            email="owner@example.com",
            password_hash=hash_password("OldStrongPass123!"),
            role_id=owner_role.role_id,
            status="Active",
            is_verified=True,
        )
        db.add(owner)
        db.flush()
        db.add(
            RefreshToken(
                user_id=owner.user_id,
                token="owner-refresh-secret",
                expires_at=datetime.utcnow() + timedelta(days=1),
            )
        )
        db.commit()
        owner_id = str(owner.user_id)

    upload_root = tmp_path / "uploads"
    avatar_dir = upload_root / "avatars"
    avatar_dir.mkdir(parents=True)
    monkeypatch.setattr(users, "UPLOAD_DIR", avatar_dir)
    monkeypatch.setattr(uploads, "UPLOAD_ROOT", upload_root)
    headers = {
        "Authorization": f"Bearer {create_access_token({'user_id': owner_id})}"
    }

    profile = client.get("/api/v1/users/profile", headers=headers)
    assert profile.status_code == 200
    assert profile.json()["username"] == "owner_account"
    assert "password_hash" not in profile.json()

    avatar = client.post(
        "/api/v1/users/profile/avatar",
        headers=headers,
        files={"file": ("avatar.png", b"test-image", "image/png")},
    )
    assert avatar.status_code == 200
    avatar_file = next(avatar_dir.iterdir())
    assert avatar_file.is_file()
    assert client.get("/api/v1/users/profile/avatar", headers=headers).content == b"test-image"

    sessions = client.get("/api/v1/users/profile/sessions", headers=headers)
    assert sessions.status_code == 200
    assert "owner-refresh-secret" not in sessions.text
    assert "token" not in sessions.json()[0]
    owner_users = client.get("/api/v1/users/", headers=headers)
    assert owner_users.status_code == 200
    assert all(user["role"]["role_name"] != "Owner" for user in owner_users.json())

    password_change = client.post(
        "/api/v1/users/profile/password",
        headers=headers,
        json={
            "old_password": "OldStrongPass123!",
            "new_password": "NewStrongPass456!",
        },
    )
    assert password_change.status_code == 200
    with Session(engine) as db:
        saved_owner = db.query(User).filter(User.user_id == owner_id).one()
        assert verify_password("NewStrongPass456!", saved_owner.password_hash)
