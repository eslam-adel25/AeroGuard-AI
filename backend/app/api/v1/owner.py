import logging
from typing import Callable
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from ...core.auth_middleware import (
    ensure_platform_owner_active,
    get_authenticated_user,
)
from ...core.customer_features import FEATURE_OPTIONS
from ...database.session import get_db
from ...models.models import (
    CustomerProfile,
    Role,
    User,
)
from ...schemas.schemas import (
    OwnerCustomerActivation,
    OwnerCustomerConfigurationUpdate,
    OwnerCustomerDetails,
    OwnerCustomerList,
    OwnerCustomerSummary,
    OwnerFeatureOption,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/owner", tags=["Owner"])

MASKED_PASSWORD = "••••••••"


def require_owner(identity: dict = Depends(get_authenticated_user)) -> dict:
    if identity.get("role") != "Owner":
        raise HTTPException(status_code=403, detail="Owner access required")
    ensure_platform_owner_active(identity["_user"])
    return identity


def _summary(profile: CustomerProfile, user: User) -> OwnerCustomerSummary:
    return OwnerCustomerSummary(
        customer_profile_id=profile.customer_profile_id,
        user_id=user.user_id,
        full_name=user.full_name,
        phone=user.phone,
        organization=user.organization,
        registration_date=user.created_at,
        last_updated=profile.updated_at,
        is_verified=bool(user.is_verified),
        workflow_status=profile.workflow_status,
        account_status=profile.account_status,
    )


def _customer_query(db: Session):
    return (
        db.query(CustomerProfile, User)
        .join(User, User.user_id == CustomerProfile.user_id)
        .options(joinedload(CustomerProfile.user).joinedload(User.role))
        .filter(~User.role.has(Role.role_name == "Owner"))
    )


def _search_filter(search: str | None):
    term = (search or "").strip()
    if not term:
        return None
    pattern = f"%{term}%"
    return or_(User.full_name.ilike(pattern), User.phone.ilike(pattern))


def _list_customers(
    db: Session,
    *,
    workflow_status: str,
    account_status: str | tuple[str, ...],
    verified_only: bool = False,
    search: str | None = None,
    limit: int,
    offset: int,
) -> OwnerCustomerList:
    query = _customer_query(db).filter(
        CustomerProfile.workflow_status == workflow_status
    )
    if isinstance(account_status, tuple):
        query = query.filter(CustomerProfile.account_status.in_(account_status))
    else:
        query = query.filter(CustomerProfile.account_status == account_status)
    if verified_only:
        query = query.filter(User.is_verified.is_(True))
    search_clause = _search_filter(search)
    if search_clause is not None:
        query = query.filter(search_clause)

    total = query.count()
    rows = (
        query.order_by(User.created_at.asc(), User.user_id.asc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    items = [_summary(profile, user) for profile, user in rows]
    return OwnerCustomerList(items=items, total=total, limit=limit, offset=offset)


def _get_profile_for_update(db: Session, profile_id: UUID):
    profile = (
        db.query(CustomerProfile)
        .filter(CustomerProfile.customer_profile_id == profile_id)
        .with_for_update()
        .first()
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="Customer profile not found")
    user = db.query(User).filter(User.user_id == profile.user_id).first()
    if user is None or (user.role and user.role.role_name == "Owner"):
        raise HTTPException(status_code=404, detail="Customer profile not found")
    return profile, user


def _commit_or_rollback(db: Session, operation: str) -> None:
    try:
        db.flush()
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Owner customer %s failed", operation)
        raise HTTPException(
            status_code=500, detail="Unable to save customer changes"
        ) from exc


def _customer_details(
    db: Session, profile_id: UUID, *, lock: bool = False
) -> OwnerCustomerDetails:
    if lock:
        profile, user = _get_profile_for_update(db, profile_id)
    else:
        profile = (
            db.query(CustomerProfile)
            .filter(CustomerProfile.customer_profile_id == profile_id)
            .first()
        )
        if profile is None:
            raise HTTPException(status_code=404, detail="Customer profile not found")
        user = db.query(User).filter(User.user_id == profile.user_id).first()
        if user is None or (user.role and user.role.role_name == "Owner"):
            raise HTTPException(status_code=404, detail="Customer profile not found")

    return OwnerCustomerDetails(
        **_summary(profile, user).dict(),
        username=user.username,
        email=user.email,
        password=MASKED_PASSWORD,
        max_camera_count=profile.max_camera_count,
        owner_notes=profile.owner_notes,
    )


def _apply_transition(
    db: Session,
    profile_id: UUID,
    transition: Callable[[CustomerProfile, User], None],
    operation: str,
) -> OwnerCustomerDetails:
    profile, user = _get_profile_for_update(db, profile_id)
    transition(profile, user)
    _commit_or_rollback(db, operation)
    db.refresh(profile)
    return _customer_details(db, profile_id)


@router.get("/features", response_model=list[OwnerFeatureOption])
def list_owner_features(_identity: dict = Depends(require_owner)):
    return FEATURE_OPTIONS


@router.get("/requests/unread", response_model=OwnerCustomerList)
def list_unread_requests(
    limit: int = Query(default=100, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _identity: dict = Depends(require_owner),
):
    return _list_customers(
        db,
        workflow_status="UNREAD",
        account_status="PENDING",
        verified_only=True,
        limit=limit,
        offset=offset,
    )


@router.get("/requests/under-review", response_model=OwnerCustomerList)
def list_under_review_requests(
    search: str | None = Query(default=None, max_length=120),
    limit: int = Query(default=100, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _identity: dict = Depends(require_owner),
):
    return _list_customers(
        db,
        workflow_status="UNDER_REVIEW",
        account_status="PENDING",
        search=search,
        limit=limit,
        offset=offset,
    )


@router.get("/customers", response_model=OwnerCustomerList)
def list_platform_customers(
    search: str | None = Query(default=None, max_length=120),
    limit: int = Query(default=100, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _identity: dict = Depends(require_owner),
):
    return _list_customers(
        db,
        workflow_status="PLATFORM_CUSTOMER",
        account_status=("ACTIVE", "INACTIVE"),
        limit=limit,
        offset=offset,
        search=search,
    )


@router.get("/customers/{customer_profile_id}", response_model=OwnerCustomerDetails)
def get_customer_details(
    customer_profile_id: UUID,
    db: Session = Depends(get_db),
    _identity: dict = Depends(require_owner),
):
    return _customer_details(db, customer_profile_id)


@router.patch(
    "/customers/{customer_profile_id}/configuration",
    response_model=OwnerCustomerDetails,
)
def save_customer_configuration(
    customer_profile_id: UUID,
    payload: OwnerCustomerConfigurationUpdate,
    db: Session = Depends(get_db),
    _identity: dict = Depends(require_owner),
):
    profile, _user = _get_profile_for_update(db, customer_profile_id)
    profile.max_camera_count = payload.max_camera_count
    profile.owner_notes = payload.owner_notes
    _commit_or_rollback(db, "configuration update")
    db.refresh(profile)
    return _customer_details(db, customer_profile_id)


@router.post(
    "/customers/{customer_profile_id}/under-review",
    response_model=OwnerCustomerDetails,
)
def move_customer_to_under_review(
    customer_profile_id: UUID,
    db: Session = Depends(get_db),
    _identity: dict = Depends(require_owner),
):
    def transition(profile: CustomerProfile, user: User) -> None:
        if (
            profile.workflow_status != "UNREAD"
            or profile.account_status != "PENDING"
            or not user.is_verified
        ):
            raise HTTPException(status_code=409, detail="Request cannot move to review")
        profile.workflow_status = "UNDER_REVIEW"

    return _apply_transition(db, customer_profile_id, transition, "review transition")


@router.post(
    "/customers/{customer_profile_id}/activate",
    response_model=OwnerCustomerDetails,
)
def activate_customer(
    customer_profile_id: UUID,
    payload: OwnerCustomerActivation | None = Body(default=None),
    db: Session = Depends(get_db),
    _identity: dict = Depends(require_owner),
):
    def transition(profile: CustomerProfile, user: User) -> None:
        if profile.workflow_status not in {"UNREAD", "UNDER_REVIEW"}:
            raise HTTPException(status_code=409, detail="Customer cannot be activated")
        if profile.account_status != "PENDING":
            raise HTTPException(status_code=409, detail="Customer is not pending")
        if not user.is_verified:
            raise HTTPException(status_code=422, detail="Customer email is not verified")
        max_camera_count = (
            payload.max_camera_count if payload is not None else profile.max_camera_count
        )
        if max_camera_count is None:
            raise HTTPException(
                status_code=422, detail="Maximum camera count must be configured"
            )
        if max_camera_count < 0:
            raise HTTPException(status_code=422, detail="Maximum camera count is invalid")
        profile.max_camera_count = max_camera_count
        profile.account_status = "ACTIVE"
        profile.workflow_status = "PLATFORM_CUSTOMER"
        profile.all_features = True
        user.status = "Active"

    return _apply_transition(db, customer_profile_id, transition, "activation")


@router.post(
    "/customers/{customer_profile_id}/deactivate",
    response_model=OwnerCustomerDetails,
)
def deactivate_customer(
    customer_profile_id: UUID,
    db: Session = Depends(get_db),
    _identity: dict = Depends(require_owner),
):
    def transition(profile: CustomerProfile, user: User) -> None:
        if (
            profile.workflow_status != "PLATFORM_CUSTOMER"
            or profile.account_status != "ACTIVE"
        ):
            raise HTTPException(status_code=409, detail="Customer is not active")
        profile.account_status = "INACTIVE"
        user.status = "Inactive"

    return _apply_transition(db, customer_profile_id, transition, "deactivation")


@router.post(
    "/customers/{customer_profile_id}/reactivate",
    response_model=OwnerCustomerDetails,
)
def reactivate_customer(
    customer_profile_id: UUID,
    db: Session = Depends(get_db),
    _identity: dict = Depends(require_owner),
):
    def transition(profile: CustomerProfile, user: User) -> None:
        if (
            profile.workflow_status != "PLATFORM_CUSTOMER"
            or profile.account_status != "INACTIVE"
        ):
            raise HTTPException(status_code=409, detail="Customer is not inactive")
        profile.account_status = "ACTIVE"
        user.status = "Active"

    return _apply_transition(db, customer_profile_id, transition, "reactivation")
