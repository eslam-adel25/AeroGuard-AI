import getpass
import logging
import re
import sys

from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database.session import SessionLocal
from ..models.models import Role, User
from ..core.security import hash_password

logger = logging.getLogger(__name__)
OWNER_INDEX_NAME = "uq_users_single_owner_role_id"


def _has_single_owner_index(db: Session, owner_role_id) -> bool:
    indexes = inspect(db.get_bind()).get_indexes("users")
    owner_index = next(
        (index for index in indexes if index["name"] == OWNER_INDEX_NAME),
        None,
    )
    if not owner_index or not owner_index.get("unique"):
        return False
    if owner_index.get("column_names") != ["role_id"]:
        return False
    dialect_options = owner_index.get("dialect_options", {})
    predicate = dialect_options.get("postgresql_where")
    if predicate is None:
        predicate = dialect_options.get("sqlite_where")
    if predicate is None:
        return False
    normalized_predicate = re.sub(r'[\s"`()]', "", str(predicate)).lower()
    owner_id = str(owner_role_id).lower()
    return normalized_predicate in {
        f"role_id='{owner_id}'",
        f"role_id='{owner_id}'::uuid",
    }


def provision_owner(
    db: Session,
    *,
    full_name: str,
    username: str,
    email: str,
    password: str,
) -> User:
    normalized_name = full_name.strip()
    normalized_username = username.strip()
    normalized_email = email.strip().lower()
    if not normalized_name:
        raise ValueError("Full name is required.")
    if len(normalized_username) < 3:
        raise ValueError("Username must be at least 3 characters.")
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized_email):
        raise ValueError("A valid email address is required.")

    try:
        owner_role = (
            db.query(Role)
            .filter(Role.role_name == "Owner")
            .with_for_update()
            .first()
        )
        if owner_role is None:
            raise RuntimeError(
                "The Owner role is missing. Apply migration 004 before provisioning."
            )
        if not _has_single_owner_index(db, owner_role.role_id):
            raise RuntimeError(
                "The single-Owner database constraint is missing. "
                "Apply migration 004 before provisioning."
            )
        if db.query(User).filter(User.role_id == owner_role.role_id).first():
            raise RuntimeError("An Owner account has already been provisioned.")
        if (
            db.query(User)
            .filter(
                (User.username == normalized_username)
                | (User.email == normalized_email)
            )
            .first()
        ):
            raise ValueError("Username or email is already registered.")

        owner = User(
            full_name=normalized_name,
            username=normalized_username,
            email=normalized_email,
            password_hash=hash_password(password),
            role_id=owner_role.role_id,
            status="Active",
            is_verified=True,
        )
        db.add(owner)
        db.commit()
        db.refresh(owner)
        return owner
    except Exception:
        db.rollback()
        raise


def main() -> int:
    try:
        full_name = input("Owner full name: ").strip()
        username = input("Owner username: ").strip()
        email = input("Owner email: ").strip()
        password = getpass.getpass("Owner password: ")
        password_confirmation = getpass.getpass("Confirm owner password: ")
        if password != password_confirmation:
            raise ValueError("Passwords do not match.")

        with SessionLocal() as db:
            owner = provision_owner(
                db,
                full_name=full_name,
                username=username,
                email=email,
                password=password,
            )
        print(f"Owner account '{owner.username}' created successfully.")
        return 0
    except (ValueError, RuntimeError) as exc:
        print(f"Owner provisioning failed: {exc}", file=sys.stderr)
        return 1
    except IntegrityError:
        print(
            "Owner provisioning failed: a conflicting account or Owner already exists.",
            file=sys.stderr,
        )
        return 1
    except (EOFError, KeyboardInterrupt):
        print("Owner provisioning cancelled.", file=sys.stderr)
        return 1
    except Exception:
        logger.exception("Unexpected Owner provisioning failure")
        print("Owner provisioning failed due to a database or system error.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
