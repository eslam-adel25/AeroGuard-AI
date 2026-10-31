import runpy
import uuid
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import (
    Boolean,
    CHAR,
    Column,
    ForeignKey,
    MetaData,
    String,
    Table,
    create_engine,
    insert,
    select,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.session import Base
from app.models.models import (
    CustomerFeaturePermission,
    CustomerProfile,
    Role,
    User,
)


def _new_user(username):
    return User(
        full_name=username,
        username=username,
        email=f"{username}@example.com",
        password_hash="test-hash",
    )


def _run_customer_profile_migration(connection):
    migration_path = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "004_customer_profiles.py"
    )
    upgrade = runpy.run_path(str(migration_path))["upgrade"]
    context = MigrationContext.configure(connection)
    with Operations.context(context):
        upgrade()


def test_customer_profile_is_one_to_one_with_user():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db:
            user = _new_user("profile_owner")
            profile = CustomerProfile(user=user)
            db.add(profile)
            db.commit()

            assert user.customer_profile is profile
            assert profile.user is user

            db.add(CustomerProfile(user_id=user.user_id))
            with pytest.raises(IntegrityError):
                db.commit()
            db.rollback()
    finally:
        engine.dispose()


def test_customer_profile_statuses_and_camera_quota_constraints():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db:
            profiles = []
            workflow_statuses = (
                "AWAITING_EMAIL_VERIFICATION",
                "UNREAD",
                "UNDER_REVIEW",
                "PLATFORM_CUSTOMER",
            )
            account_statuses = ("PENDING", "ACTIVE", "INACTIVE")
            for index, workflow_status in enumerate(workflow_statuses):
                user = _new_user(f"workflow_{index}")
                profile = CustomerProfile(
                    user=user,
                    workflow_status=workflow_status,
                    account_status=account_statuses[index % len(account_statuses)],
                )
                db.add(profile)
                profiles.append(profile)

            unlimited_user = _new_user("unlimited_quota")
            unlimited = CustomerProfile(user=unlimited_user, max_camera_count=None)
            zero_user = _new_user("zero_quota")
            zero = CustomerProfile(user=zero_user, max_camera_count=0)
            inactive_customer_user = _new_user("inactive_platform_customer")
            inactive_customer = CustomerProfile(
                user=inactive_customer_user,
                workflow_status="PLATFORM_CUSTOMER",
                account_status="INACTIVE",
            )
            db.add_all([unlimited, zero, inactive_customer])
            db.commit()

            assert unlimited.max_camera_count is None
            assert zero.max_camera_count == 0
            assert inactive_customer.workflow_status == "PLATFORM_CUSTOMER"
            assert inactive_customer.account_status == "INACTIVE"

            with pytest.raises(ValueError, match="non-negative"):
                CustomerProfile(max_camera_count=-1)

            with pytest.raises(IntegrityError):
                db.query(CustomerProfile).filter(
                    CustomerProfile.customer_profile_id == zero.customer_profile_id
                ).update({CustomerProfile.max_camera_count: -1})
                db.commit()
            db.rollback()

            with pytest.raises(IntegrityError):
                db.add(
                    CustomerProfile(
                        user=_new_user("invalid_workflow"),
                        workflow_status="NOT_A_STATUS",
                    )
                )
                db.commit()
            db.rollback()

            with pytest.raises(IntegrityError):
                db.add(
                    CustomerProfile(
                        user=_new_user("invalid_account_status"),
                        account_status="NOT_A_STATUS",
                    )
                )
                db.commit()
            db.rollback()
    finally:
        engine.dispose()


def test_customer_feature_permissions_allow_many_keys_but_reject_duplicates():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db:
            user = _new_user("feature_customer")
            profile = CustomerProfile(user=user, all_features=True)
            profile.feature_permissions.extend(
                [
                    CustomerFeaturePermission(
                        feature_key="face_recognition", is_allowed=True
                    ),
                    CustomerFeaturePermission(
                        feature_key="loitering", is_allowed=False
                    ),
                ]
            )
            db.add(profile)
            db.commit()

            assert profile.all_features is True
            assert {permission.feature_key for permission in profile.feature_permissions} == {
                "face_recognition",
                "loitering",
            }

            db.add(
                CustomerFeaturePermission(
                    customer_profile_id=profile.customer_profile_id,
                    feature_key="loitering",
                    is_allowed=True,
                )
            )
            with pytest.raises(IntegrityError):
                db.commit()
            db.rollback()
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    ("require_email_verification", "expected_customers"),
    [
        (
            True,
            {
                "verified_pending",
                "verified_without_role",
                "legacy_admin_one",
                "legacy_admin_two",
            },
        ),
        (
            False,
            {
                "verified_pending",
                "verified_without_role",
                "unverified_active",
                "legacy_admin_one",
                "legacy_admin_two",
            },
        ),
    ],
)
def test_migration_backfills_legacy_customers_idempotently_and_preserves_ownership(
    monkeypatch, require_email_verification, expected_customers
):
    monkeypatch.setenv(
        "REQUIRE_EMAIL_VERIFICATION",
        "true" if require_email_verification else "false",
    )
    engine = create_engine("sqlite:///:memory:")
    metadata = MetaData()
    roles = Table(
        "roles",
        metadata,
        Column("role_id", CHAR(36), primary_key=True),
        Column("role_name", String(50), nullable=False, unique=True),
    )
    users = Table(
        "users",
        metadata,
        Column("user_id", CHAR(36), primary_key=True),
        Column("role_id", CHAR(36), ForeignKey("roles.role_id")),
        Column("is_verified", Boolean),
        Column("status", String(20)),
    )
    cameras = Table(
        "cameras",
        metadata,
        Column("camera_id", CHAR(36), primary_key=True),
        Column("owner_id", CHAR(36), ForeignKey("users.user_id"), nullable=False),
    )

    role_ids = {
        "Officer": str(uuid.uuid4()),
        "Admin": str(uuid.uuid4()),
        "Administrator": str(uuid.uuid4()),
    }
    user_ids = {
        "verified_pending": str(uuid.uuid4()),
        "verified_admin": str(uuid.uuid4()),
        "legacy_admin_one": str(uuid.uuid4()),
        "legacy_admin_two": str(uuid.uuid4()),
        "unverified_active": str(uuid.uuid4()),
        "verified_without_role": str(uuid.uuid4()),
    }

    try:
        with engine.begin() as connection:
            metadata.create_all(connection)
            connection.execute(
                insert(roles),
                [
                    {"role_id": role_ids["Officer"], "role_name": "Officer"},
                    {
                        "role_id": role_ids["Admin"],
                        "role_name": "Admin",
                    },
                    {
                        "role_id": role_ids["Administrator"],
                        "role_name": "Administrator",
                    },
                ],
            )
            connection.execute(
                insert(users),
                [
                    {
                        "user_id": user_ids["verified_pending"],
                        "role_id": role_ids["Officer"],
                        "is_verified": True,
                        "status": "Pending",
                    },
                    {
                        "user_id": user_ids["verified_admin"],
                        "role_id": role_ids["Administrator"],
                        "is_verified": True,
                        "status": "Active",
                    },
                    {
                        "user_id": user_ids["legacy_admin_one"],
                        "role_id": role_ids["Admin"],
                        "is_verified": True,
                        "status": "Active",
                    },
                    {
                        "user_id": user_ids["legacy_admin_two"],
                        "role_id": role_ids["Admin"],
                        "is_verified": True,
                        "status": "Active",
                    },
                    {
                        "user_id": user_ids["unverified_active"],
                        "role_id": role_ids["Officer"],
                        "is_verified": False,
                        "status": "Active",
                    },
                    {
                        "user_id": user_ids["verified_without_role"],
                        "role_id": None,
                        "is_verified": True,
                        "status": "Inactive",
                    },
                ],
            )
            camera_id = str(uuid.uuid4())
            connection.execute(
                insert(cameras).values(
                    camera_id=camera_id,
                    owner_id=user_ids["verified_pending"],
                )
            )

            users_before = connection.execute(
                select(
                    users.c.user_id,
                    users.c.role_id,
                    users.c.is_verified,
                    users.c.status,
                ).order_by(users.c.user_id)
            ).all()
            camera_before = connection.execute(select(cameras)).all()

            _run_customer_profile_migration(connection)
            _run_customer_profile_migration(connection)

            profiles = Table(
                "customer_profiles", MetaData(), autoload_with=connection
            )
            profile_rows = connection.execute(
                select(
                    profiles.c.user_id,
                    profiles.c.workflow_status,
                    profiles.c.account_status,
                    profiles.c.max_camera_count,
                    profiles.c.all_features,
                    profiles.c.activation_date,
                )
            ).all()
            profile_map = {row.user_id: row for row in profile_rows}

            assert set(profile_map) == {
                user_ids[name] for name in expected_customers
            }
            assert len(profile_rows) == len(expected_customers)
            for row in profile_rows:
                assert row.workflow_status == "PLATFORM_CUSTOMER"
                assert row.account_status == "ACTIVE"
                assert row.max_camera_count is None
                assert row.all_features is True
                assert row.activation_date is None

            owner_role_id = connection.execute(
                select(roles.c.role_id).where(roles.c.role_name == "Owner")
            ).scalar_one()
            assert connection.execute(
                select(roles.c.role_id).where(roles.c.role_name == "Owner")
            ).all() == [(owner_role_id,)]
            assert connection.execute(
                select(
                    users.c.user_id,
                    users.c.role_id,
                    users.c.is_verified,
                    users.c.status,
                ).order_by(users.c.user_id)
            ).all() == users_before
            assert connection.execute(select(cameras)).all() == camera_before

            connection.execute(
                insert(users).values(
                    user_id=str(uuid.uuid4()),
                    role_id=owner_role_id,
                    is_verified=True,
                    status="Active",
                )
            )
            with pytest.raises(IntegrityError):
                with connection.begin_nested():
                    connection.execute(
                        insert(users).values(
                            user_id=str(uuid.uuid4()),
                            role_id=owner_role_id,
                            is_verified=True,
                            status="Active",
                        )
                    )
    finally:
        engine.dispose()


def test_migration_preserves_profiles_created_by_startup_create_all():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db:
            role = Role(role_name="Officer")
            user = _new_user("preexisting_profile")
            profile = CustomerProfile(
                user=user,
                workflow_status="UNDER_REVIEW",
                account_status="PENDING",
                all_features=False,
            )
            db.add_all([role, profile])
            db.commit()
            existing_profile_id = profile.customer_profile_id

        with engine.begin() as connection:
            _run_customer_profile_migration(connection)
            _run_customer_profile_migration(connection)

            profiles = Table(
                "customer_profiles", MetaData(), autoload_with=connection
            )
            rows = connection.execute(
                select(profiles.c.customer_profile_id, profiles.c.workflow_status)
            ).all()
            assert rows == [(str(existing_profile_id), "UNDER_REVIEW")]
    finally:
        engine.dispose()
