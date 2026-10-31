import logging
from uuid import UUID

from fastapi import Depends, HTTPException
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from ..database.session import get_db
from ..models.models import Camera, CustomerProfile, Role, User
from .auth_middleware import get_resource_user, is_admin_role

logger = logging.getLogger(__name__)
PLATFORM_TENANT_SCOPE = "*"


def customer_profile_for_user(user: User) -> CustomerProfile | None:
    role_name = user.role.role_name if user.role else None
    if role_name == "Owner":
        return None
    if role_name == "Officer":
        return user.customer_membership
    if is_admin_role(role_name):
        primary_profile = user.customer_profile
        member_profile = user.customer_membership
        if primary_profile is None or primary_profile.user_id != user.user_id:
            return None
        if (
            member_profile is not None
            and member_profile.customer_profile_id
            != primary_profile.customer_profile_id
        ):
            logger.error(
                "Admin tenant membership conflicts with primary profile for user %s",
                user.user_id,
            )
            return None
        return member_profile or primary_profile
    return None


def tenant_id_from_identity(identity: dict) -> UUID:
    tenant_id = identity.get("customer_profile_id")
    try:
        return UUID(str(tenant_id))
    except (TypeError, ValueError, AttributeError) as exc:
        user_id = identity.get("user_id")
        logger.warning(
            "Denied tenant access for user %s without verified customer membership",
            user_id,
        )
        raise HTTPException(
            status_code=403,
            detail="Customer membership is not configured",
        ) from exc


async def require_tenant_context(
    current_user: dict = Depends(get_resource_user),
) -> dict:
    if current_user.get("role") == "Owner":
        current_user["customer_profile_id"] = PLATFORM_TENANT_SCOPE
        return current_user
    if current_user.get("role") not in {"Admin", "Administrator", "Officer"}:
        raise HTTPException(status_code=403, detail="Customer access required")
    current_user["customer_profile_id"] = str(
        tenant_id_from_identity(current_user)
    )
    return current_user


def tenant_member_user_ids(db: Session, tenant_id: UUID | str):
    if str(tenant_id) == PLATFORM_TENANT_SCOPE:
        return db.query(User.user_id)
    profile_owner = (
        db.query(CustomerProfile.customer_profile_id)
        .filter(
            CustomerProfile.customer_profile_id == tenant_id,
            CustomerProfile.user_id == User.user_id,
        )
        .exists()
    )
    return db.query(User.user_id).filter(
        or_(
            User.customer_profile_id == tenant_id,
            and_(User.role.has(Role.role_name.in_(["Admin", "Administrator"])), profile_owner),
        )
    )


def tenant_camera_ids(db: Session, tenant_id: UUID | str):
    if str(tenant_id) == PLATFORM_TENANT_SCOPE:
        return db.query(Camera.camera_id)
    member_ids = tenant_member_user_ids(db, tenant_id)
    return db.query(Camera.camera_id).filter(
        or_(
            Camera.customer_profile_id == tenant_id,
            and_(
                Camera.customer_profile_id.is_(None),
                Camera.owner_id.in_(member_ids),
            ),
        )
    )


def tenant_owner_filter(
    model, db: Session, tenant_id: UUID | str, owner_column
):
    if str(tenant_id) == PLATFORM_TENANT_SCOPE:
        return True
    member_ids = tenant_member_user_ids(db, tenant_id)
    return or_(
        model.customer_profile_id == tenant_id,
        and_(
            model.customer_profile_id.is_(None),
            owner_column.in_(member_ids),
        ),
    )


def tenant_camera_child_filter(
    model,
    db: Session,
    tenant_id: UUID | str,
    *,
    owner_column=None,
    actor_column=None,
):
    if str(tenant_id) == PLATFORM_TENANT_SCOPE:
        return True
    camera_ids = tenant_camera_ids(db, tenant_id)
    legacy_filters = [
        model.customer_profile_id.is_(None),
    ]
    member_ids = tenant_member_user_ids(db, tenant_id)
    if owner_column is not None:
        legacy_filters.append(owner_column.in_(member_ids))
    if actor_column is not None:
        legacy_filters.append(
            or_(actor_column.is_(None), actor_column.in_(member_ids))
        )
    return and_(
        model.camera_id.in_(camera_ids),
        or_(
            model.customer_profile_id == tenant_id,
            and_(*legacy_filters),
        ),
    )


def require_tenant_profile(
    db: Session,
    identity: dict,
) -> CustomerProfile:
    if identity.get("customer_profile_id") == PLATFORM_TENANT_SCOPE:
        raise HTTPException(
            status_code=403,
            detail="A specific customer profile is required",
        )
    tenant_id = tenant_id_from_identity(identity)
    profile = (
        db.query(CustomerProfile)
        .filter(CustomerProfile.customer_profile_id == tenant_id)
        .first()
    )
    if profile is None:
        logger.error(
            "Tenant membership references missing profile for user %s",
            identity.get("user_id"),
        )
        raise HTTPException(
            status_code=403,
            detail="Customer membership is not configured",
        )
    return profile
