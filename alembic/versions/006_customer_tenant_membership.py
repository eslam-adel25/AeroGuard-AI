"""Add nullable customer membership and resource tenant keys.

No existing user or resource is assigned to a tenant by this revision.
Ambiguous legacy ownership must be reviewed and backfilled separately.

Revision ID: 006_customer_tenant_membership
Revises: 005_restore_abandoned_bag
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "006_customer_tenant_membership"
down_revision: Union[str, None] = "005_restore_abandoned_bag"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TENANT_COLUMNS = {
    "users": "customer_profile_id",
    "cameras": "customer_profile_id",
    "restricted_zones": "customer_profile_id",
    "detections": "customer_profile_id",
    "trackings": "customer_profile_id",
    "ai_events": "customer_profile_id",
    "reports": "customer_profile_id",
    "user_settings": "customer_profile_id",
}


def _ensure_column(table: str, column: str) -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table, schema="public"):
        raise RuntimeError(f"Required table public.{table} is missing.")
    if column in {
        item["name"] for item in inspector.get_columns(table, schema="public")
    }:
        return
    op.add_column(
        table,
        sa.Column(
            column,
            sa.UUID(),
            sa.ForeignKey(
                "customer_profiles.customer_profile_id",
                name=(
                    "fk_users_customer_profile"
                    if table == "users"
                    else None
                ),
            ),
            nullable=True,
        ),
        schema="public",
    )


def _ensure_index(table: str, name: str) -> None:
    inspector = sa.inspect(op.get_bind())
    indexes = {
        item["name"] for item in inspector.get_indexes(table, schema="public")
    }
    if name not in indexes:
        op.create_index(
            name,
            table,
            ["customer_profile_id"],
            unique=False,
            schema="public",
        )


def _ensure_unique(table: str, name: str, columns: list[str]) -> None:
    inspector = sa.inspect(op.get_bind())
    constraints = {
        item["name"]
        for item in inspector.get_unique_constraints(table, schema="public")
    }
    if name not in constraints:
        op.create_unique_constraint(name, table, columns, schema="public")


def _ensure_composite_fk(
    table: str,
    name: str,
    local_columns: list[str],
    remote_table: str,
    remote_columns: list[str],
) -> None:
    inspector = sa.inspect(op.get_bind())
    constraints = {
        item["name"]
        for item in inspector.get_foreign_keys(table, schema="public")
    }
    if name not in constraints:
        op.create_foreign_key(
            name,
            table,
            remote_table,
            local_columns,
            remote_columns,
            source_schema="public",
            referent_schema="public",
        )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("customer_profiles", schema="public"):
        raise RuntimeError(
            "Customer profiles must exist before tenant membership can be added."
        )

    for table, column in TENANT_COLUMNS.items():
        _ensure_column(table, column)
        _ensure_index(table, f"ix_{table}_customer_profile_id")

    _ensure_unique(
        "cameras",
        "uq_cameras_id_customer_profile",
        ["camera_id", "customer_profile_id"],
    )
    _ensure_unique(
        "trackings",
        "uq_trackings_id_customer_profile",
        ["track_id", "customer_profile_id"],
    )
    for table in ("restricted_zones", "detections", "trackings", "ai_events"):
        _ensure_composite_fk(
            table,
            f"fk_{table}_camera_tenant",
            ["camera_id", "customer_profile_id"],
            "cameras",
            ["camera_id", "customer_profile_id"],
        )
    _ensure_composite_fk(
        "ai_events",
        "fk_ai_events_track_tenant",
        ["track_id", "customer_profile_id"],
        "trackings",
        ["track_id", "customer_profile_id"],
    )
def downgrade() -> None:
    raise RuntimeError(
        "Tenant ownership keys may contain reviewed assignments; use a separately "
        "reviewed rollback procedure instead of dropping them automatically."
    )
