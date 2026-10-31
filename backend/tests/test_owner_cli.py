import pytest
from sqlalchemy import Index, create_engine
from sqlalchemy.orm import Session

from app.cli.create_owner import provision_owner
from app.core.security import verify_password
from app.database.session import Base
from app.models.models import CustomerProfile, Role, User


def test_owner_provisioning_is_verified_active_and_one_time():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db:
            role = Role(role_name="Owner")
            db.add(role)
            db.flush()
            Index(
                "uq_users_single_owner_role_id",
                User.role_id,
                unique=True,
                sqlite_where=User.role_id == role.role_id,
            ).create(engine)

            owner = provision_owner(
                db,
                full_name="First Owner",
                username="first_owner",
                email="owner@example.com",
                password="StrongPass123!",
            )
            assert owner.is_verified is True
            assert owner.status == "Active"
            assert owner.role.role_name == "Owner"
            assert verify_password("StrongPass123!", owner.password_hash)
            assert db.query(CustomerProfile).count() == 0

            with pytest.raises(RuntimeError, match="already been provisioned"):
                provision_owner(
                    db,
                    full_name="Second Owner",
                    username="second_owner",
                    email="second@example.com",
                    password="AnotherPass123!",
                )
    finally:
        engine.dispose()
