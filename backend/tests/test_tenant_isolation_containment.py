import asyncio

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.auth_middleware import (
    ensure_platform_owner_active,
    user_access_metadata,
)
from app.core.tenant import require_tenant_context
from app.database.session import Base
from app.models.models import CustomerProfile, Role, User


def test_customer_routes_require_a_verified_tenant_membership():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        admin_role = Role(role_name="Admin")
        officer_role = Role(role_name="Officer")
        db.add_all([admin_role, officer_role])
        db.flush()
        admin = User(
            full_name="Tenant Admin",
            username="tenant_admin",
            email="tenant_admin@example.com",
            password_hash="not-used",
            role=admin_role,
        )
        admin.customer_profile = CustomerProfile(
            workflow_status="PLATFORM_CUSTOMER",
            account_status="ACTIVE",
            all_features=True,
        )
        unmapped_officer = User(
            full_name="Unmapped Officer",
            username="unmapped_officer",
            email="unmapped_officer@example.com",
            password_hash="not-used",
            role=officer_role,
        )
        unmapped_officer.customer_profile = CustomerProfile(
            workflow_status="PLATFORM_CUSTOMER",
            account_status="ACTIVE",
            all_features=True,
        )
        db.add_all([admin, unmapped_officer])
        db.flush()
        admin.customer_profile_id = admin.customer_profile.customer_profile_id
        db.commit()

        admin_identity = user_access_metadata(admin)
        assert admin_identity["customer_profile_id"] == str(
            admin.customer_profile.customer_profile_id
        )
        assert asyncio.run(require_tenant_context(admin_identity))[
            "customer_profile_id"
        ] == str(admin.customer_profile.customer_profile_id)

        officer_identity = user_access_metadata(unmapped_officer)
        assert officer_identity["customer_profile_id"] is None
        with pytest.raises(HTTPException) as denied:
            asyncio.run(require_tenant_context(officer_identity))
        assert denied.value.status_code == 403

    engine.dispose()


def test_inactive_platform_owner_is_denied():
    owner = User(
        full_name="Inactive Owner",
        username="inactive_owner",
        email="inactive_owner@example.com",
        password_hash="not-used",
        role=Role(role_name="Owner"),
        status="Inactive",
        is_verified=True,
    )
    with pytest.raises(HTTPException) as denied:
        ensure_platform_owner_active(owner)
    assert denied.value.status_code == 403
