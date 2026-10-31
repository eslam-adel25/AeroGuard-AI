import os
from uuid import UUID

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session, joinedload

from ..database.session import get_db
from ..models.models import User
from .security import verify_token


def is_admin_role(role_name: str | None) -> bool:
    return role_name in {"Admin", "Administrator"}


def _email_verification_required() -> bool:
    value = (os.getenv("REQUIRE_EMAIL_VERIFICATION") or "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def user_access_metadata(user: User) -> dict:
    from .tenant import customer_profile_for_user

    profile = customer_profile_for_user(user)
    if profile is None and user.role and user.role.role_name == "Officer":
        profile = user.customer_profile
    if user.role and user.role.role_name == "Owner":
        workflow_status = None
        account_status = "ACTIVE"
    elif profile:
        workflow_status = profile.workflow_status
        account_status = profile.account_status
    else:
        workflow_status = "PLATFORM_CUSTOMER"
        account_status = "ACTIVE"

    return {
        "user_id": user.user_id,
        "username": user.username,
        "role": user.role.role_name if user.role else None,
        "is_verified": bool(user.is_verified),
        "workflow_status": workflow_status,
        "account_status": account_status,
        "is_owner": bool(user.role and user.role.role_name == "Owner"),
        "customer_profile_id": (
            str(profile.customer_profile_id)
            if profile is not None
            and (
                user.role
                and (
                    user.role.role_name == "Officer"
                    and user.customer_membership is profile
                    or user.role.role_name in {"Admin", "Administrator"}
                    and profile.user_id == user.user_id
                )
            )
            else None
        ),
    }


def ensure_user_can_access_platform(user: User) -> None:
    role_name = user.role.role_name if user.role else None
    if role_name == "Owner":
        raise HTTPException(
            status_code=403,
            detail="Owner accounts do not have customer platform access",
        )
    account_status = (user.status or "").strip().lower()
    if account_status != "active":
        detail = (
            "Account is inactive"
            if account_status == "inactive"
            else "Account is awaiting activation"
        )
        raise HTTPException(status_code=403, detail=detail)

    from .tenant import customer_profile_for_user

    profile = customer_profile_for_user(user)
    if profile is None:
        profile = user.customer_profile
    if profile is None:
        if _email_verification_required() and not user.is_verified:
            raise HTTPException(status_code=403, detail="Email not verified")
        # Legacy profile-less accounts retain self-service access; tenant
        # resource routes independently require verified membership.
        return

    if profile.account_status != "ACTIVE":
        detail = (
            "Account is inactive"
            if profile.account_status == "INACTIVE"
            else "Account is awaiting activation"
        )
        raise HTTPException(status_code=403, detail=detail)

    if profile.workflow_status != "PLATFORM_CUSTOMER":
        raise HTTPException(status_code=403, detail="Account is awaiting activation")

    # Phase 1 grandfathered active customers, even when email verification was
    # not enabled when their accounts were created.


def ensure_platform_owner_active(user: User) -> None:
    if not user.role or user.role.role_name != "Owner":
        raise HTTPException(status_code=403, detail="Owner access required")
    if (user.status or "").strip().lower() != "active":
        raise HTTPException(status_code=403, detail="Account is inactive")
    if _email_verification_required() and not user.is_verified:
        raise HTTPException(status_code=403, detail="Email not verified")


def load_user_from_token(token: str, db: Session) -> User:
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    raw_user_id = payload.get("user_id")
    try:
        user_id = UUID(str(raw_user_id))
    except (TypeError, ValueError, AttributeError):
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = (
        db.query(User)
        .options(
            joinedload(User.role),
            joinedload(User.customer_profile),
            joinedload(User.customer_membership),
        )
        .filter(User.user_id == user_id)
        .first()
    )
    if user is None:
        raise HTTPException(status_code=401, detail="User no longer exists")
    return user


async def get_authenticated_user(
    authorization: str = Header(None),
    token: str | None = None,
    db: Session = Depends(get_db),
):
    """Resolve the current identity and role from the database, not JWT claims."""
    bearer_token = None
    if authorization and authorization.startswith("Bearer "):
        bearer_token = authorization.split(" ", 1)[1].strip()

    if not bearer_token and token:
        bearer_token = token

    if not bearer_token:
        raise HTTPException(status_code=401, detail="Unauthorized: No token provided")

    user = load_user_from_token(bearer_token, db)
    identity = user_access_metadata(user)
    identity["_user"] = user
    return identity


async def get_current_user(
    identity: dict = Depends(get_authenticated_user),
):
    user = identity["_user"]
    ensure_user_can_access_platform(user)
    return {key: value for key, value in identity.items() if key != "_user"}


async def get_resource_user(
    identity: dict = Depends(get_authenticated_user),
):
    """Authorize customer resource APIs or the platform Owner."""
    user = identity["_user"]
    if identity.get("role") == "Owner":
        ensure_platform_owner_active(user)
    else:
        ensure_user_can_access_platform(user)
    return {key: value for key, value in identity.items() if key != "_user"}


async def require_tenant_isolation(
    current_user: dict = Depends(get_resource_user),
):
    from .tenant import require_tenant_context

    return await require_tenant_context(current_user)


async def get_self_service_user(
    identity: dict = Depends(get_authenticated_user),
):
    """Allow an authenticated identity to manage only its own account."""
    user = identity["_user"]
    if identity.get("role") != "Owner":
        ensure_user_can_access_platform(user)
    return {key: value for key, value in identity.items() if key != "_user"}


def role_required(allowed_roles: list):
    async def role_checker(current_user: dict = Depends(get_resource_user)):
        user_role = current_user.get("role")
        role_allowed = user_role in allowed_roles or (
            "Administrator" in allowed_roles and is_admin_role(user_role)
        )
        if not role_allowed:
            raise HTTPException(status_code=403, detail="ليس لديك صلاحية للقيام بهذا الإجراء")
        return current_user
    return role_checker


def is_user_currently_authorized(
    user_id: str, feature: str | None = None
) -> bool:
    from ..database.session import SessionLocal
    from ..models.models import User
    from sqlalchemy.orm import joinedload

    db = SessionLocal()
    try:
        try:
            parsed_user_id = UUID(str(user_id))
        except (TypeError, ValueError, AttributeError):
            return False
        user = (
            db.query(User)
            .options(
                joinedload(User.role),
                joinedload(User.customer_profile),
                joinedload(User.customer_membership),
            )
            .filter(User.user_id == parsed_user_id)
            .first()
        )
        if user is None:
            return False
        if user.role is not None and user.role.role_name == "Owner":
            try:
                ensure_platform_owner_active(user)
            except HTTPException:
                return False
            return feature is None
        from .tenant import customer_profile_for_user

        if customer_profile_for_user(user) is None:
            return False
        try:
            ensure_user_can_access_platform(user)
        except HTTPException:
            return False
        if user.role is None or user.role.role_name == "Owner":
            return False
        if feature is not None:
            from .customer_features import has_customer_feature

            return has_customer_feature(
                db, str(user.user_id), user.role.role_name, feature
            )
        return True
    finally:
        db.close()