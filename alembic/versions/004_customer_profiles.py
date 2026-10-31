"""Add customer profiles, feature permissions, and the Owner role foundation.

Revision ID: 004_customer_profiles
Revises: 003_abandoned_bag_timeout
"""
from typing import Sequence, Union
import os
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "004_customer_profiles"
down_revision: Union[str, None] = "003_abandoned_bag_timeout"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _uuid_type():
    return sa.CHAR(36).with_variant(postgresql.UUID(as_uuid=True), "postgresql")


def _new_uuid(bind):
    value = uuid.uuid4()
    return value if bind.dialect.name == "postgresql" else str(value)


def _require_legacy_schema(bind):
    inspector = sa.inspect(bind)
    if not inspector.has_table("users") or not inspector.has_table("roles"):
        raise RuntimeError("The users and roles tables must exist before this revision.")

    required_columns = {
        "users": {"user_id", "role_id", "is_verified"},
        "roles": {"role_id", "role_name"},
    }
    for table_name, required in required_columns.items():
        present = {column["name"] for column in inspector.get_columns(table_name)}
        missing = required - present
        if missing:
            missing_names = ", ".join(sorted(missing))
            raise RuntimeError(
                f"The {table_name} table is missing required columns: {missing_names}."
            )


def _create_tables(bind):
    inspector = sa.inspect(bind)
    if not inspector.has_table("customer_profiles"):
        op.create_table(
            "customer_profiles",
            sa.Column("customer_profile_id", _uuid_type(), nullable=False),
            sa.Column("user_id", _uuid_type(), nullable=False),
            sa.Column(
                "workflow_status",
                sa.String(length=32),
                server_default="AWAITING_EMAIL_VERIFICATION",
                nullable=False,
            ),
            sa.Column(
                "account_status",
                sa.String(length=16),
                server_default="PENDING",
                nullable=False,
            ),
            sa.Column("max_camera_count", sa.Integer(), nullable=True),
            sa.Column(
                "all_features",
                sa.Boolean(),
                server_default=sa.false(),
                nullable=False,
            ),
            sa.Column("activation_date", sa.DateTime(timezone=True), nullable=True),
            sa.Column("owner_notes", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=True,
            ),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.CheckConstraint(
                "workflow_status IN "
                "('AWAITING_EMAIL_VERIFICATION', 'UNREAD', 'UNDER_REVIEW', "
                "'PLATFORM_CUSTOMER')",
                name="ck_customer_profiles_workflow_status",
            ),
            sa.CheckConstraint(
                "account_status IN ('PENDING', 'ACTIVE', 'INACTIVE')",
                name="ck_customer_profiles_account_status",
            ),
            sa.CheckConstraint(
                "max_camera_count IS NULL OR max_camera_count >= 0",
                name="ck_customer_profiles_max_camera_count_nonnegative",
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.user_id"]),
            sa.PrimaryKeyConstraint("customer_profile_id"),
            sa.UniqueConstraint("user_id", name="uq_customer_profiles_user_id"),
        )

    inspector = sa.inspect(bind)
    if not inspector.has_table("customer_feature_permissions"):
        op.create_table(
            "customer_feature_permissions",
            sa.Column("permission_id", _uuid_type(), nullable=False),
            sa.Column("customer_profile_id", _uuid_type(), nullable=False),
            sa.Column("feature_key", sa.String(length=100), nullable=False),
            sa.Column(
                "is_allowed", sa.Boolean(), server_default=sa.false(), nullable=False
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=True,
            ),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.CheckConstraint(
                "length(trim(feature_key)) > 0",
                name="ck_customer_feature_permissions_feature_key_nonempty",
            ),
            sa.ForeignKeyConstraint(
                ["customer_profile_id"],
                ["customer_profiles.customer_profile_id"],
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("permission_id"),
            sa.UniqueConstraint(
                "customer_profile_id",
                "feature_key",
                name="uq_customer_feature_permissions_profile_feature",
            ),
        )


def _ensure_index(bind, table_name, index_name, columns):
    existing = {index["name"] for index in sa.inspect(bind).get_indexes(table_name)}
    if index_name not in existing:
        op.create_index(index_name, table_name, columns, unique=False)


def _seed_owner_role(bind):
    roles = sa.Table("roles", sa.MetaData(), autoload_with=bind)
    owner_role_id = bind.execute(
        sa.select(roles.c.role_id).where(roles.c.role_name == "Owner")
    ).scalar_one_or_none()

    if owner_role_id is None:
        owner_role_id = _new_uuid(bind)
        bind.execute(
            roles.insert().values(role_id=owner_role_id, role_name="Owner")
        )

    users = sa.Table("users", sa.MetaData(), autoload_with=bind)
    owner_user_count = bind.execute(
        sa.select(sa.func.count())
        .select_from(users)
        .where(users.c.role_id == owner_role_id)
    ).scalar_one()
    if owner_user_count > 1:
        raise RuntimeError(
            "Cannot enforce the single-Owner constraint: "
            f"{owner_user_count} users already have the Owner role."
        )

    if bind.dialect.name not in {"postgresql", "sqlite"}:
        raise RuntimeError(
            "The single-Owner constraint requires PostgreSQL or SQLite partial indexes."
        )

    role_id_literal = str(uuid.UUID(str(owner_role_id)))
    predicate = sa.text(f"role_id = '{role_id_literal}'")
    existing_indexes = {
        index["name"]: index for index in sa.inspect(bind).get_indexes("users")
    }
    index_name = "uq_users_single_owner_role_id"
    if index_name in existing_indexes:
        index = existing_indexes[index_name]
        if not index["unique"] or index["column_names"] != ["role_id"]:
            raise RuntimeError(
                f"Existing index {index_name} does not enforce the Owner constraint."
            )
    else:
        op.create_index(
            index_name,
            "users",
            ["role_id"],
            unique=True,
            postgresql_where=predicate,
            sqlite_where=predicate,
        )


def _backfill_legacy_customers(bind):
    users = sa.Table("users", sa.MetaData(), autoload_with=bind)
    roles = sa.Table("roles", sa.MetaData(), autoload_with=bind)
    profiles = sa.Table("customer_profiles", sa.MetaData(), autoload_with=bind)

    query = sa.select(users.c.user_id).select_from(
        users.outerjoin(roles, users.c.role_id == roles.c.role_id)
    )
    if (os.getenv("REQUIRE_EMAIL_VERIFICATION") or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }:
        query = query.where(users.c.is_verified.is_(True))
    query = query.where(
        sa.func.lower(sa.func.trim(sa.func.coalesce(roles.c.role_name, "")))
        != "administrator"
    )
    qualifying_user_ids = list(bind.execute(query).scalars())
    existing_user_ids = set(bind.execute(sa.select(profiles.c.user_id)).scalars())

    for user_id in qualifying_user_ids:
        if user_id in existing_user_ids:
            continue
        bind.execute(
            profiles.insert().values(
                customer_profile_id=_new_uuid(bind),
                user_id=user_id,
                workflow_status="PLATFORM_CUSTOMER",
                account_status="ACTIVE",
                max_camera_count=None,
                all_features=True,
                activation_date=None,
            )
        )
        existing_user_ids.add(user_id)


def upgrade() -> None:
    bind = op.get_bind()
    _require_legacy_schema(bind)
    _create_tables(bind)

    _ensure_index(
        bind,
        "customer_profiles",
        "ix_customer_profiles_workflow_status",
        ["workflow_status"],
    )
    _ensure_index(
        bind,
        "customer_profiles",
        "ix_customer_profiles_account_status",
        ["account_status"],
    )

    _seed_owner_role(bind)
    _backfill_legacy_customers(bind)


def downgrade() -> None:
    raise RuntimeError(
        "This migration is intentionally non-destructive; customer profile data "
        "must be preserved during rollback."
    )
