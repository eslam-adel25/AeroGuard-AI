"""Normalize saved abandoned-bag thresholds to the fixed 60-second workflow.

Revision ID: 003_abandoned_bag_timeout
Revises: 002_prod_schema_baseline
Create Date: 2026-08-16 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = "003_abandoned_bag_timeout"
down_revision: Union[str, None] = "002_prod_schema_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "UPDATE system_settings "
        "SET abandoned_bag_seconds = 60 "
        "WHERE abandoned_bag_seconds IS NULL OR abandoned_bag_seconds != 60"
    )
    op.execute(
        "UPDATE user_settings "
        "SET abandoned_bag_seconds = 60 "
        "WHERE abandoned_bag_seconds IS NULL OR abandoned_bag_seconds != 60"
    )


def downgrade() -> None:
    pass
