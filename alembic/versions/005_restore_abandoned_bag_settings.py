"""Restore abandoned-bag values captured before revision 003.

Revision ID: 005_restore_abandoned_bag
Revises: 004_customer_profiles
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "005_restore_abandoned_bag"
down_revision: Union[str, None] = "004_customer_profiles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

USER_SNAPSHOT = "adoption_user_settings_snapshot"
SYSTEM_SNAPSHOT = "adoption_system_settings_snapshot"


def _validate_snapshot(bind, table_name, expected_columns):
    inspector = sa.inspect(bind)
    if not inspector.has_table(table_name, schema="public"):
        raise RuntimeError(
            f"Required adoption snapshot table public.{table_name} is missing."
        )

    columns = {
        column["name"]
        for column in inspector.get_columns(table_name, schema="public")
    }
    if columns != expected_columns:
        raise RuntimeError(
            f"Adoption snapshot table public.{table_name} has an unexpected schema."
        )


def _require_matching_rows(bind, query, table_name):
    mismatch_count = bind.execute(sa.text(query)).scalar_one()
    if mismatch_count:
        raise RuntimeError(
            f"Adoption snapshot public.{table_name} does not match the live rows "
            f"({mismatch_count} identity mismatch(es))."
        )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    user_snapshot_exists = inspector.has_table(USER_SNAPSHOT, schema="public")
    system_snapshot_exists = inspector.has_table(SYSTEM_SNAPSHOT, schema="public")

    if not user_snapshot_exists and not system_snapshot_exists:
        user_settings_count = bind.execute(
            sa.text("SELECT count(*) FROM public.user_settings")
        ).scalar_one()
        system_settings_count = bind.execute(
            sa.text("SELECT count(*) FROM public.system_settings")
        ).scalar_one()
        if user_settings_count or system_settings_count:
            raise RuntimeError(
                "Existing settings rows require identity-keyed snapshots before "
                "revision 003 can be adopted."
            )
        return
    if user_snapshot_exists != system_snapshot_exists:
        raise RuntimeError(
            "Both user and system settings snapshots are required for adoption."
        )

    _validate_snapshot(
        bind,
        USER_SNAPSHOT,
        {"settings_id", "owner_id", "abandoned_bag_seconds"},
    )
    _validate_snapshot(
        bind,
        SYSTEM_SNAPSHOT,
        {"id", "abandoned_bag_seconds"},
    )

    _require_matching_rows(
        bind,
        f"""
        SELECT count(*)
        FROM public.user_settings AS live
        FULL OUTER JOIN public.{USER_SNAPSHOT} AS saved
          ON saved.settings_id = live.settings_id
        WHERE live.settings_id IS NULL
           OR saved.settings_id IS NULL
           OR live.owner_id IS DISTINCT FROM saved.owner_id
        """,
        USER_SNAPSHOT,
    )
    _require_matching_rows(
        bind,
        f"""
        SELECT count(*)
        FROM public.system_settings AS live
        FULL OUTER JOIN public.{SYSTEM_SNAPSHOT} AS saved
          ON saved.id = live.id
        WHERE live.id IS NULL OR saved.id IS NULL
        """,
        SYSTEM_SNAPSHOT,
    )

    bind.execute(
        sa.text(
            f"""
            UPDATE public.user_settings AS live
            SET abandoned_bag_seconds = saved.abandoned_bag_seconds
            FROM public.{USER_SNAPSHOT} AS saved
            WHERE live.settings_id = saved.settings_id
              AND live.owner_id = saved.owner_id
              AND live.abandoned_bag_seconds
                  IS DISTINCT FROM saved.abandoned_bag_seconds
            """
        )
    )
    bind.execute(
        sa.text(
            f"""
            UPDATE public.system_settings AS live
            SET abandoned_bag_seconds = saved.abandoned_bag_seconds
            FROM public.{SYSTEM_SNAPSHOT} AS saved
            WHERE live.id = saved.id
              AND live.abandoned_bag_seconds
                  IS DISTINCT FROM saved.abandoned_bag_seconds
            """
        )
    )

    _require_matching_rows(
        bind,
        f"""
        SELECT count(*)
        FROM public.user_settings AS live
        JOIN public.{USER_SNAPSHOT} AS saved
          ON saved.settings_id = live.settings_id
         AND saved.owner_id = live.owner_id
        WHERE live.abandoned_bag_seconds
              IS DISTINCT FROM saved.abandoned_bag_seconds
        """,
        USER_SNAPSHOT,
    )
    _require_matching_rows(
        bind,
        f"""
        SELECT count(*)
        FROM public.system_settings AS live
        JOIN public.{SYSTEM_SNAPSHOT} AS saved ON saved.id = live.id
        WHERE live.abandoned_bag_seconds
              IS DISTINCT FROM saved.abandoned_bag_seconds
        """,
        SYSTEM_SNAPSHOT,
    )

    op.drop_table(USER_SNAPSHOT, schema="public")
    op.drop_table(SYSTEM_SNAPSHOT, schema="public")


def downgrade() -> None:
    raise RuntimeError(
        "Restored abandoned-bag values cannot be downgraded without a new snapshot."
    )
