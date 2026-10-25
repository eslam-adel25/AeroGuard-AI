"""Production schema baseline alignment from revision 001.

Revision ID: 002_prod_schema_baseline
Revises: 001
Create Date: 2026-08-15 00:00:00.000000

This migration updates the schema produced by revision 001 to match the
current live production schema shape, based on read-only metadata comparison.
It contains schema operations only (no data migration).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "002_prod_schema_baseline"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

JSON_TO_JSONB_TYPE_CHANGES = [
    ('activity_logs', 'details', 'json', 'jsonb'),
    ('ai_events', 'metadata', 'json', 'jsonb'),
    ('reports', 'charts', 'json', 'jsonb'),
    ('reports', 'details', 'json', 'jsonb'),
    ('reports', 'export_history', 'json', 'jsonb'),
    ('reports', 'filters', 'json', 'jsonb'),
    ('reports', 'summary', 'json', 'jsonb'),
    ('restricted_zones', 'polygon_coords', 'json', 'jsonb'),
    ('trackings', 'latest_bbox', 'json', 'jsonb'),
]

DEFAULTS_TO_DROP = [
    ('cameras', 'camera_type'),
    ('cameras', 'status'),
    ('detections', 'is_violation'),
    ('email_verifications', 'attempts'),
    ('email_verifications', 'resend_count'),
    ('refresh_tokens', 'revoked'),
    ('reports', 'report_type'),
    ('restricted_zones', 'zone_type'),
    ('system_settings', 'abandoned_bag_enabled'),
    ('system_settings', 'abandoned_bag_seconds'),
    ('system_settings', 'airport_name'),
    ('system_settings', 'crowd_density_enabled'),
    ('system_settings', 'crowd_density_threshold'),
    ('system_settings', 'default_fps'),
    ('system_settings', 'detection_confidence'),
    ('system_settings', 'enable_alert_sounds'),
    ('system_settings', 'face_recognition_enabled'),
    ('system_settings', 'fire_detection_enabled'),
    ('system_settings', 'frame_skip'),
    ('system_settings', 'gpu_enabled'),
    ('system_settings', 'jpeg_quality'),
    ('system_settings', 'jwt_expiration'),
    ('system_settings', 'language'),
    ('system_settings', 'loitering_enabled'),
    ('system_settings', 'loitering_seconds'),
    ('system_settings', 'organization_name'),
    ('system_settings', 'restricted_area_enabled'),
    ('system_settings', 'smoke_detection_enabled'),
    ('system_settings', 'system_name'),
    ('system_settings', 'timezone'),
    ('system_settings', 'tracker_backend'),
    ('system_settings', 'tracking_enabled'),
    ('system_settings', 'video_resolution'),
    ('system_settings', 'wrong_direction_angle_threshold'),
    ('system_settings', 'wrong_direction_enabled'),
    ('trackings', 'track_type'),
    ('user_settings', 'abandoned_bag_enabled'),
    ('user_settings', 'abandoned_bag_seconds'),
    ('user_settings', 'accent_color'),
    ('user_settings', 'airport_name'),
    ('user_settings', 'alert_duration'),
    ('user_settings', 'alert_volume'),
    ('user_settings', 'auto_reconnect'),
    ('user_settings', 'bitrate'),
    ('user_settings', 'compression'),
    ('user_settings', 'compression_enabled'),
    ('user_settings', 'crowd_density_enabled'),
    ('user_settings', 'crowd_density_threshold'),
    ('user_settings', 'dashboard_layout'),
    ('user_settings', 'date_format'),
    ('user_settings', 'default_camera_resolution'),
    ('user_settings', 'default_fps'),
    ('user_settings', 'desktop_notifications'),
    ('user_settings', 'detection_confidence'),
    ('user_settings', 'detection_fps'),
    ('user_settings', 'enable_alert_sounds'),
    ('user_settings', 'face_detection_enabled'),
    ('user_settings', 'face_recognition_enabled'),
    ('user_settings', 'fire_detection_enabled'),
    ('user_settings', 'frame_buffer'),
    ('user_settings', 'frame_skip'),
    ('user_settings', 'gpu_enabled'),
    ('user_settings', 'jpeg_quality'),
    ('user_settings', 'jwt_expiration'),
    ('user_settings', 'language'),
    ('user_settings', 'loitering_enabled'),
    ('user_settings', 'loitering_seconds'),
    ('user_settings', 'max_objects'),
    ('user_settings', 'min_alert_confidence'),
    ('user_settings', 'object_detection_enabled'),
    ('user_settings', 'organization_name'),
    ('user_settings', 'password_policy'),
    ('user_settings', 'profile_language'),
    ('user_settings', 'recording_quality'),
    ('user_settings', 'remember_me_default'),
    ('user_settings', 'restricted_area_enabled'),
    ('user_settings', 'session_timeout'),
    ('user_settings', 'show_alert_labels'),
    ('user_settings', 'sidebar_state'),
    ('user_settings', 'smoke_detection_enabled'),
    ('user_settings', 'stream_video_resolution'),
    ('user_settings', 'system_name'),
    ('user_settings', 'theme'),
    ('user_settings', 'time_format'),
    ('user_settings', 'timezone'),
    ('user_settings', 'tracking_enabled'),
    ('user_settings', 'video_resolution'),
    ('user_settings', 'wrong_direction_angle_threshold'),
    ('user_settings', 'wrong_direction_enabled'),
    ('users', 'is_verified'),
    ('users', 'status'),
]

DEFAULTS_TO_RESTORE = [
    ('cameras', 'camera_type', "'LIVE'::character varying"),
    ('cameras', 'status', "'Offline'::character varying"),
    ('detections', 'is_violation', 'false'),
    ('email_verifications', 'attempts', '0'),
    ('email_verifications', 'resend_count', '0'),
    ('refresh_tokens', 'revoked', 'false'),
    ('reports', 'report_type', "'custom'::character varying"),
    ('restricted_zones', 'zone_type', "'Restricted Area'::character varying"),
    ('system_settings', 'abandoned_bag_enabled', 'false'),
    ('system_settings', 'abandoned_bag_seconds', '60'),
    ('system_settings', 'airport_name', "'Main Airport'::character varying"),
    ('system_settings', 'crowd_density_enabled', 'false'),
    ('system_settings', 'crowd_density_threshold', '10'),
    ('system_settings', 'default_fps', '30'),
    ('system_settings', 'detection_confidence', "'0.5'::double precision"),
    ('system_settings', 'enable_alert_sounds', 'true'),
    ('system_settings', 'face_recognition_enabled', 'true'),
    ('system_settings', 'fire_detection_enabled', 'false'),
    ('system_settings', 'frame_skip', '0'),
    ('system_settings', 'gpu_enabled', 'false'),
    ('system_settings', 'jpeg_quality', '70'),
    ('system_settings', 'jwt_expiration', '60'),
    ('system_settings', 'language', "'en'::character varying"),
    ('system_settings', 'loitering_enabled', 'false'),
    ('system_settings', 'loitering_seconds', '30'),
    ('system_settings', 'organization_name', "'AeroGuard AI'::character varying"),
    ('system_settings', 'restricted_area_enabled', 'false'),
    ('system_settings', 'smoke_detection_enabled', 'false'),
    ('system_settings', 'system_name', "'AeroGuard AI'::character varying"),
    ('system_settings', 'timezone', "'UTC'::character varying"),
    ('system_settings', 'tracker_backend', "'iou'::character varying"),
    ('system_settings', 'tracking_enabled', 'true'),
    ('system_settings', 'video_resolution', "'720p'::character varying"),
    ('system_settings', 'wrong_direction_angle_threshold', '150'),
    ('system_settings', 'wrong_direction_enabled', 'false'),
    ('trackings', 'track_type', "'person'::character varying"),
    ('user_settings', 'abandoned_bag_enabled', 'false'),
    ('user_settings', 'abandoned_bag_seconds', '60'),
    ('user_settings', 'accent_color', "'#3b82f6'::character varying"),
    ('user_settings', 'airport_name', "''::character varying"),
    ('user_settings', 'alert_duration', '5'),
    ('user_settings', 'alert_volume', '80'),
    ('user_settings', 'auto_reconnect', 'true'),
    ('user_settings', 'bitrate', "'2000k'::character varying"),
    ('user_settings', 'compression', "'h264'::character varying"),
    ('user_settings', 'compression_enabled', 'true'),
    ('user_settings', 'crowd_density_enabled', 'false'),
    ('user_settings', 'crowd_density_threshold', '10'),
    ('user_settings', 'dashboard_layout', "'default'::character varying"),
    ('user_settings', 'date_format', "'YYYY-MM-DD'::character varying"),
    ('user_settings', 'default_camera_resolution', "'720p'::character varying"),
    ('user_settings', 'default_fps', '30'),
    ('user_settings', 'desktop_notifications', 'true'),
    ('user_settings', 'detection_confidence', "'0.5'::double precision"),
    ('user_settings', 'detection_fps', '15'),
    ('user_settings', 'enable_alert_sounds', 'true'),
    ('user_settings', 'face_detection_enabled', 'false'),
    ('user_settings', 'face_recognition_enabled', 'false'),
    ('user_settings', 'fire_detection_enabled', 'false'),
    ('user_settings', 'frame_buffer', '5'),
    ('user_settings', 'frame_skip', '0'),
    ('user_settings', 'gpu_enabled', 'false'),
    ('user_settings', 'jpeg_quality', '75'),
    ('user_settings', 'jwt_expiration', '60'),
    ('user_settings', 'language', "'en'::character varying"),
    ('user_settings', 'loitering_enabled', 'false'),
    ('user_settings', 'loitering_seconds', '30'),
    ('user_settings', 'max_objects', '10'),
    ('user_settings', 'min_alert_confidence', "'0.5'::double precision"),
    ('user_settings', 'object_detection_enabled', 'true'),
    ('user_settings', 'organization_name', "''::character varying"),
    ('user_settings', 'password_policy', "'min:8,upper:1,digit:1'::character varying"),
    ('user_settings', 'profile_language', "'en'::character varying"),
    ('user_settings', 'recording_quality', "'medium'::character varying"),
    ('user_settings', 'remember_me_default', 'true'),
    ('user_settings', 'restricted_area_enabled', 'false'),
    ('user_settings', 'session_timeout', '30'),
    ('user_settings', 'show_alert_labels', 'true'),
    ('user_settings', 'sidebar_state', "'expanded'::character varying"),
    ('user_settings', 'smoke_detection_enabled', 'false'),
    ('user_settings', 'stream_video_resolution', "'720p'::character varying"),
    ('user_settings', 'system_name', "'AeroGuard AI'::character varying"),
    ('user_settings', 'theme', "'light'::character varying"),
    ('user_settings', 'time_format', "'24h'::character varying"),
    ('user_settings', 'timezone', "'UTC'::character varying"),
    ('user_settings', 'tracking_enabled', 'true'),
    ('user_settings', 'video_resolution', "'720p'::character varying"),
    ('user_settings', 'wrong_direction_angle_threshold', '150'),
    ('user_settings', 'wrong_direction_enabled', 'false'),
    ('users', 'is_verified', 'false'),
    ('users', 'status', "'Pending'::character varying"),
]

UNIQUE_CONSTRAINTS_TO_DROP = [
    ('email_verifications', 'email_verifications_token_key'),
    ('refresh_tokens', 'refresh_tokens_token_key'),
    ('user_settings', 'user_settings_owner_id_key'),
    ('users', 'users_email_key'),
    ('users', 'users_username_key'),
]

INDEXES_TO_MAKE_UNIQUE = [
    ('email_verifications', 'ix_email_verifications_token', ('token',)),
    ('refresh_tokens', 'ix_refresh_tokens_token', ('token',)),
    ('user_settings', 'ix_user_settings_owner_id', ('owner_id',)),
    ('users', 'ix_users_email', ('email',)),
    ('users', 'ix_users_username', ('username',)),
]

def upgrade() -> None:
    # 1) Align JSON/JSONB types with production.
    for table_name, column_name, _old_type, _new_type in JSON_TO_JSONB_TYPE_CHANGES:
        op.execute(
            f'ALTER TABLE "{table_name}" ALTER COLUMN "{column_name}" TYPE JSONB USING "{column_name}"::jsonb'
        )

    # 2) Remove defaults that are absent in production.
    for table_name, column_name in DEFAULTS_TO_DROP:
        op.alter_column(table_name, column_name, server_default=None)

    # 3) Replace UNIQUE constraints with unique standalone indexes where production uses indexes.
    for table_name, constraint_name in UNIQUE_CONSTRAINTS_TO_DROP:
        op.drop_constraint(constraint_name, table_name, type_="unique")

    for table_name, index_name, columns in INDEXES_TO_MAKE_UNIQUE:
        op.drop_index(index_name, table_name=table_name)
        op.create_index(index_name, table_name, list(columns), unique=True)


def downgrade() -> None:
    # Reverse index/constraint shape back to revision 001 behavior.
    for table_name, index_name, columns in INDEXES_TO_MAKE_UNIQUE:
        op.drop_index(index_name, table_name=table_name)
        op.create_index(index_name, table_name, list(columns), unique=False)

    for table_name, constraint_name in UNIQUE_CONSTRAINTS_TO_DROP:
        # Constraint names map to single-column UNIQUE constraints in revision 001.
        if constraint_name == "email_verifications_token_key":
            op.create_unique_constraint(constraint_name, table_name, ["token"])
        elif constraint_name == "refresh_tokens_token_key":
            op.create_unique_constraint(constraint_name, table_name, ["token"])
        elif constraint_name == "user_settings_owner_id_key":
            op.create_unique_constraint(constraint_name, table_name, ["owner_id"])
        elif constraint_name == "users_email_key":
            op.create_unique_constraint(constraint_name, table_name, ["email"])
        elif constraint_name == "users_username_key":
            op.create_unique_constraint(constraint_name, table_name, ["username"])

    # Restore server defaults that revision 001 set.
    for table_name, column_name, default_sql in DEFAULTS_TO_RESTORE:
        op.alter_column(table_name, column_name, server_default=sa.text(default_sql))

    # Restore JSON types from revision 001.
    for table_name, column_name, _old_type, _new_type in reversed(JSON_TO_JSONB_TYPE_CHANGES):
        op.execute(
            f'ALTER TABLE "{table_name}" ALTER COLUMN "{column_name}" TYPE JSON USING "{column_name}"::json'
        )
