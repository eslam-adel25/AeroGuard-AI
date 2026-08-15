"""Initial schema - captures the current database structure

Revision ID: 001
Revises: 
Create Date: 2026-08-14 00:00:00.000000

This is the initial migration created from the existing SQLAlchemy models.
It represents the current production schema without any modifications.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create roles table
    op.create_table(
        'roles',
        sa.Column('role_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role_name', sa.String(50), nullable=False),
        sa.PrimaryKeyConstraint('role_id'),
        sa.UniqueConstraint('role_name')
    )

    # Create users table
    op.create_table(
        'users',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('full_name', sa.String(150), nullable=False),
        sa.Column('username', sa.String(50), nullable=False),
        sa.Column('email', sa.String(120), nullable=False),
        sa.Column('password_hash', sa.Text(), nullable=False),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('organization', sa.String(150), nullable=True),
        sa.Column('profile_picture', sa.Text(), nullable=True),
        sa.Column('status', sa.String(20), nullable=True, server_default='Pending'),
        sa.Column('is_verified', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('last_login', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=True, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.user_id'], ),
        sa.ForeignKeyConstraint(['role_id'], ['roles.role_id'], ),
        sa.ForeignKeyConstraint(['updated_by'], ['users.user_id'], ),
        sa.PrimaryKeyConstraint('user_id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username')
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=False)
    op.create_index('ix_users_username', 'users', ['username'], unique=False)

    # Create system_settings table
    op.create_table(
        'system_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_name', sa.String(150), nullable=True, server_default='AeroGuard AI'),
        sa.Column('airport_name', sa.String(150), nullable=True, server_default='Main Airport'),
        sa.Column('language', sa.String(10), nullable=True, server_default='en'),
        sa.Column('timezone', sa.String(50), nullable=True, server_default='UTC'),
        sa.Column('system_name', sa.String(100), nullable=True, server_default='AeroGuard AI'),
        sa.Column('detection_confidence', sa.Float(), nullable=True, server_default='0.5'),
        sa.Column('tracking_enabled', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('face_recognition_enabled', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('enable_alert_sounds', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('default_fps', sa.Integer(), nullable=True, server_default='30'),
        sa.Column('video_resolution', sa.String(20), nullable=True, server_default='720p'),
        sa.Column('jpeg_quality', sa.Integer(), nullable=True, server_default='70'),
        sa.Column('jwt_expiration', sa.Integer(), nullable=True, server_default='60'),
        sa.Column('gpu_enabled', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('frame_skip', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('tracker_backend', sa.String(50), nullable=True, server_default='iou'),
        sa.Column('loitering_enabled', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('loitering_seconds', sa.Integer(), nullable=True, server_default='30'),
        sa.Column('crowd_density_enabled', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('crowd_density_threshold', sa.Integer(), nullable=True, server_default='10'),
        sa.Column('abandoned_bag_enabled', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('abandoned_bag_seconds', sa.Integer(), nullable=True, server_default='20'),
        sa.Column('wrong_direction_enabled', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('wrong_direction_angle_threshold', sa.Integer(), nullable=True, server_default='150'),
        sa.Column('restricted_area_enabled', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('fire_detection_enabled', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('smoke_detection_enabled', sa.Boolean(), nullable=True, server_default='false'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create cameras table
    op.create_table(
        'cameras',
        sa.Column('camera_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('camera_name', sa.String(100), nullable=False),
        sa.Column('location', sa.String(150), nullable=False),
        sa.Column('stream_url', sa.Text(), nullable=False),
        sa.Column('camera_type', sa.String(20), nullable=True, server_default='LIVE'),
        sa.Column('status', sa.String(20), nullable=True, server_default='Offline'),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=True, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['owner_id'], ['users.user_id'], ),
        sa.PrimaryKeyConstraint('camera_id')
    )
    op.create_index('ix_cameras_owner_id', 'cameras', ['owner_id'], unique=False)

    # Create restricted_zones table
    op.create_table(
        'restricted_zones',
        sa.Column('zone_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('camera_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('zone_name', sa.String(100), nullable=False),
        sa.Column('zone_type', sa.String(50), nullable=True, server_default='Restricted Area'),
        sa.Column('polygon_coords', postgresql.JSON(), nullable=False),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['camera_id'], ['cameras.camera_id'], ),
        sa.ForeignKeyConstraint(['owner_id'], ['users.user_id'], ),
        sa.PrimaryKeyConstraint('zone_id')
    )
    op.create_index('ix_restricted_zones_owner_id', 'restricted_zones', ['owner_id'], unique=False)

    # Create detections table
    op.create_table(
        'detections',
        sa.Column('detection_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('camera_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('detection_type', sa.String(50), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('priority', sa.String(20), nullable=True),
        sa.Column('is_violation', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('violation_type', sa.String(50), nullable=True),
        sa.Column('detected_at', sa.TIMESTAMP(timezone=True), nullable=True, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['camera_id'], ['cameras.camera_id'], ),
        sa.ForeignKeyConstraint(['owner_id'], ['users.user_id'], ),
        sa.PrimaryKeyConstraint('detection_id')
    )
    op.create_index('ix_detections_owner_id', 'detections', ['owner_id'], unique=False)

    # Create email_verifications table
    op.create_table(
        'email_verifications',
        sa.Column('token_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('token', sa.String(255), nullable=False),
        sa.Column('otp_code', sa.String(20), nullable=True),
        sa.Column('new_email', sa.String(255), nullable=True),
        sa.Column('new_username', sa.String(100), nullable=True),
        sa.Column('expires_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('resend_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=True, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ),
        sa.PrimaryKeyConstraint('token_id'),
        sa.UniqueConstraint('token')
    )
    op.create_index('ix_email_verifications_token', 'email_verifications', ['token'], unique=False)
    op.create_index('ix_email_verifications_user_id', 'email_verifications', ['user_id'], unique=False)

    # Create refresh_tokens table
    op.create_table(
        'refresh_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('token', sa.String(255), nullable=False),
        sa.Column('expires_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('revoked', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=True, server_default=sa.text('now()')),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('operating_system', sa.String(100), nullable=True),
        sa.Column('browser', sa.String(100), nullable=True),
        sa.Column('device_category', sa.String(50), nullable=True),
        sa.Column('device_type', sa.String(200), nullable=True),
        sa.Column('device_model', sa.String(100), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token')
    )
    op.create_index('ix_refresh_tokens_token', 'refresh_tokens', ['token'], unique=False)
    op.create_index('ix_refresh_tokens_user_id', 'refresh_tokens', ['user_id'], unique=False)

    # Create activity_logs table
    op.create_table(
        'activity_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('details', postgresql.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(50), nullable=True),
        sa.Column('user_agent', sa.String(300), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=True, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_activity_logs_user_id', 'activity_logs', ['user_id'], unique=False)

    # Create user_settings table
    op.create_table(
        'user_settings',
        sa.Column('settings_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_name', sa.String(150), nullable=True, server_default=''),
        sa.Column('airport_name', sa.String(150), nullable=True, server_default=''),
        sa.Column('system_name', sa.String(100), nullable=True, server_default='AeroGuard AI'),
        sa.Column('language', sa.String(10), nullable=True, server_default='en'),
        sa.Column('timezone', sa.String(50), nullable=True, server_default='UTC'),
        sa.Column('date_format', sa.String(20), nullable=True, server_default='YYYY-MM-DD'),
        sa.Column('time_format', sa.String(20), nullable=True, server_default='24h'),
        sa.Column('detection_confidence', sa.Float(), nullable=True, server_default='0.5'),
        sa.Column('tracking_enabled', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('object_detection_enabled', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('face_detection_enabled', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('face_recognition_enabled', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('max_objects', sa.Integer(), nullable=True, server_default='10'),
        sa.Column('detection_fps', sa.Integer(), nullable=True, server_default='15'),
        sa.Column('default_fps', sa.Integer(), nullable=True, server_default='30'),
        sa.Column('recording_quality', sa.String(20), nullable=True, server_default='medium'),
        sa.Column('frame_buffer', sa.Integer(), nullable=True, server_default='5'),
        sa.Column('auto_reconnect', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('default_camera_resolution', sa.String(20), nullable=True, server_default='720p'),
        sa.Column('stream_video_resolution', sa.String(20), nullable=True, server_default='720p'),
        sa.Column('video_resolution', sa.String(20), nullable=True, server_default='720p'),
        sa.Column('jpeg_quality', sa.Integer(), nullable=True, server_default='75'),
        sa.Column('compression', sa.String(50), nullable=True, server_default='h264'),
        sa.Column('compression_enabled', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('bitrate', sa.String(50), nullable=True, server_default='2000k'),
        sa.Column('enable_alert_sounds', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('alert_duration', sa.Integer(), nullable=True, server_default='5'),
        sa.Column('alert_volume', sa.Integer(), nullable=True, server_default='80'),
        sa.Column('min_alert_confidence', sa.Float(), nullable=True, server_default='0.5'),
        sa.Column('show_alert_labels', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('desktop_notifications', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('gpu_enabled', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('frame_skip', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('loitering_enabled', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('loitering_seconds', sa.Integer(), nullable=True, server_default='30'),
        sa.Column('crowd_density_enabled', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('crowd_density_threshold', sa.Integer(), nullable=True, server_default='10'),
        sa.Column('abandoned_bag_enabled', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('abandoned_bag_seconds', sa.Integer(), nullable=True, server_default='20'),
        sa.Column('wrong_direction_enabled', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('wrong_direction_angle_threshold', sa.Integer(), nullable=True, server_default='150'),
        sa.Column('restricted_area_enabled', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('fire_detection_enabled', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('smoke_detection_enabled', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('jwt_expiration', sa.Integer(), nullable=True, server_default='60'),
        sa.Column('session_timeout', sa.Integer(), nullable=True, server_default='30'),
        sa.Column('password_policy', sa.String(200), nullable=True, server_default='min:8,upper:1,digit:1'),
        sa.Column('remember_me_default', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('theme', sa.String(20), nullable=True, server_default='light'),
        sa.Column('profile_language', sa.String(10), nullable=True, server_default='en'),
        sa.Column('sidebar_state', sa.String(20), nullable=True, server_default='expanded'),
        sa.Column('dashboard_layout', sa.String(50), nullable=True, server_default='default'),
        sa.Column('accent_color', sa.String(20), nullable=True, server_default='#3b82f6'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=True, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['owner_id'], ['users.user_id'], ),
        sa.PrimaryKeyConstraint('settings_id'),
        sa.UniqueConstraint('owner_id')
    )
    op.create_index('ix_user_settings_owner_id', 'user_settings', ['owner_id'], unique=False)

    # Create reports table
    op.create_table(
        'reports',
        sa.Column('report_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('generated_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('generated_at', sa.TIMESTAMP(timezone=True), nullable=True, server_default=sa.text('now()')),
        sa.Column('title', sa.String(200), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('report_type', sa.String(50), nullable=True, server_default='custom'),
        sa.Column('filters', postgresql.JSON(), nullable=True),
        sa.Column('summary', postgresql.JSON(), nullable=True),
        sa.Column('charts', postgresql.JSON(), nullable=True),
        sa.Column('details', postgresql.JSON(), nullable=True),
        sa.Column('export_history', postgresql.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['generated_by'], ['users.user_id'], ),
        sa.ForeignKeyConstraint(['owner_id'], ['users.user_id'], ),
        sa.PrimaryKeyConstraint('report_id')
    )
    op.create_index('ix_reports_owner_id', 'reports', ['owner_id'], unique=False)

    # Create trackings table
    op.create_table(
        'trackings',
        sa.Column('track_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('camera_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('track_type', sa.String(50), nullable=True, server_default='person'),
        sa.Column('track_label', sa.String(150), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=True, server_default=sa.text('now()')),
        sa.Column('last_seen_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('latest_bbox', postgresql.JSON(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['camera_id'], ['cameras.camera_id'], ),
        sa.PrimaryKeyConstraint('track_id')
    )
    op.create_index('ix_trackings_camera_id', 'trackings', ['camera_id'], unique=False)

    # Create ai_events table
    op.create_table(
        'ai_events',
        sa.Column('event_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('track_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('camera_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('detected_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('detection_type', sa.String(100), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('screenshot_path', sa.String(400), nullable=True),
        sa.Column('metadata', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=True, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['camera_id'], ['cameras.camera_id'], ),
        sa.ForeignKeyConstraint(['detected_by'], ['users.user_id'], ),
        sa.ForeignKeyConstraint(['track_id'], ['trackings.track_id'], ),
        sa.PrimaryKeyConstraint('event_id')
    )
    op.create_index('ix_ai_events_camera_id', 'ai_events', ['camera_id'], unique=False)
    op.create_index('ix_ai_events_track_id', 'ai_events', ['track_id'], unique=False)


def downgrade() -> None:
    # Drop all tables in reverse order to respect foreign key constraints
    op.drop_index('ix_ai_events_track_id', table_name='ai_events')
    op.drop_index('ix_ai_events_camera_id', table_name='ai_events')
    op.drop_table('ai_events')
    
    op.drop_index('ix_trackings_camera_id', table_name='trackings')
    op.drop_table('trackings')
    
    op.drop_index('ix_reports_owner_id', table_name='reports')
    op.drop_table('reports')
    
    op.drop_index('ix_user_settings_owner_id', table_name='user_settings')
    op.drop_table('user_settings')
    
    op.drop_index('ix_activity_logs_user_id', table_name='activity_logs')
    op.drop_table('activity_logs')
    
    op.drop_index('ix_refresh_tokens_token', table_name='refresh_tokens')
    op.drop_index('ix_refresh_tokens_user_id', table_name='refresh_tokens')
    op.drop_table('refresh_tokens')
    
    op.drop_index('ix_email_verifications_token', table_name='email_verifications')
    op.drop_index('ix_email_verifications_user_id', table_name='email_verifications')
    op.drop_table('email_verifications')
    
    op.drop_index('ix_detections_owner_id', table_name='detections')
    op.drop_table('detections')
    
    op.drop_index('ix_restricted_zones_owner_id', table_name='restricted_zones')
    op.drop_table('restricted_zones')
    
    op.drop_index('ix_cameras_owner_id', table_name='cameras')
    op.drop_table('cameras')
    
    op.drop_table('system_settings')
    
    op.drop_index('ix_users_username', table_name='users')
    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')
    
    op.drop_table('roles')
