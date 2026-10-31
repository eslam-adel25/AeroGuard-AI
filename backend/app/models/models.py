import uuid
from sqlalchemy import (
    CHAR,
    Boolean,
    CheckConstraint,
    Column,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    JSON,
    String,
    Text,
    TIMESTAMP,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func
from sqlalchemy.types import TypeDecorator
from ..database.session import Base

JSONB = JSON


class GUID(TypeDecorator):
    impl = CHAR
    cache_ok = True

    def __init__(self, as_uuid: bool = False, *args, **kwargs):
        self.as_uuid = as_uuid
        super().__init__(*args, **kwargs)

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=self.as_uuid))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        if isinstance(value, uuid.UUID):
            return str(value)
        return str(uuid.UUID(value))

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        return value if isinstance(value, uuid.UUID) else uuid.UUID(value)


UUID = GUID

class Role(Base):
    __tablename__ = "roles"
    role_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role_name = Column(String(50), nullable=False, unique=True)
    users = relationship("User", back_populates="role")

class User(Base):
    __tablename__ = "users"
    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.role_id"))
    customer_profile_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "customer_profiles.customer_profile_id",
            use_alter=True,
            name="fk_users_customer_profile",
        ),
        nullable=True,
        index=True,
    )
    full_name = Column(String(150), nullable=False)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(Text, nullable=False)
    phone = Column(String(20))
    organization = Column(String(150))
    profile_picture = Column(Text)
    status = Column(String(20), default="Pending")
    is_verified = Column(Boolean, default=False)
    last_login = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now(), nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    updated_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)

    role = relationship("Role", back_populates="users")
    cameras = relationship("Camera", back_populates="owner", foreign_keys="Camera.owner_id")
    detections = relationship("Detection", back_populates="owner", foreign_keys="Detection.owner_id")
    reports = relationship("Report", back_populates="owner", foreign_keys="Report.owner_id")
    ai_events = relationship("AIEvent", back_populates="owner", foreign_keys="AIEvent.detected_by")
    customer_profile = relationship(
        "CustomerProfile",
        back_populates="user",
        uselist=False,
        foreign_keys="CustomerProfile.user_id",
    )
    customer_membership = relationship(
        "CustomerProfile",
        back_populates="members",
        foreign_keys=[customer_profile_id],
    )


class CustomerProfile(Base):
    __tablename__ = "customer_profiles"
    __table_args__ = (
        CheckConstraint(
            "workflow_status IN "
            "('AWAITING_EMAIL_VERIFICATION', 'UNREAD', 'UNDER_REVIEW', "
            "'PLATFORM_CUSTOMER')",
            name="ck_customer_profiles_workflow_status",
        ),
        CheckConstraint(
            "account_status IN ('PENDING', 'ACTIVE', 'INACTIVE')",
            name="ck_customer_profiles_account_status",
        ),
        CheckConstraint(
            "max_camera_count IS NULL OR max_camera_count >= 0",
            name="ck_customer_profiles_max_camera_count_nonnegative",
        ),
        UniqueConstraint("user_id", name="uq_customer_profiles_user_id"),
        Index("ix_customer_profiles_workflow_status", "workflow_status"),
        Index("ix_customer_profiles_account_status", "account_status"),
    )

    customer_profile_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id"),
        nullable=False,
    )
    workflow_status = Column(
        String(32),
        nullable=False,
        default="AWAITING_EMAIL_VERIFICATION",
        server_default="AWAITING_EMAIL_VERIFICATION",
    )
    account_status = Column(
        String(16), nullable=False, default="PENDING", server_default="PENDING"
    )
    max_camera_count = Column(Integer, nullable=True)
    all_features = Column(Boolean, nullable=False, default=False, server_default="false")
    activation_date = Column(TIMESTAMP(timezone=True), nullable=True)
    owner_notes = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now(), nullable=True)

    user = relationship(
        "User",
        back_populates="customer_profile",
        foreign_keys=[user_id],
    )
    members = relationship(
        "User",
        back_populates="customer_membership",
        foreign_keys="User.customer_profile_id",
    )
    feature_permissions = relationship(
        "CustomerFeaturePermission",
        back_populates="customer_profile",
        cascade="all, delete-orphan",
    )

    @validates("max_camera_count")
    def validate_max_camera_count(self, key, value):
        if value is not None and value < 0:
            raise ValueError("max_camera_count must be non-negative")
        return value


class CustomerFeaturePermission(Base):
    __tablename__ = "customer_feature_permissions"
    __table_args__ = (
        CheckConstraint(
            "length(trim(feature_key)) > 0",
            name="ck_customer_feature_permissions_feature_key_nonempty",
        ),
        UniqueConstraint(
            "customer_profile_id",
            "feature_key",
            name="uq_customer_feature_permissions_profile_feature",
        ),
    )

    permission_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_profile_id = Column(
        UUID(as_uuid=True),
        ForeignKey("customer_profiles.customer_profile_id", ondelete="CASCADE"),
        nullable=False,
    )
    feature_key = Column(String(100), nullable=False)
    is_allowed = Column(Boolean, nullable=False, default=False, server_default="false")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now(), nullable=True)

    customer_profile = relationship(
        "CustomerProfile", back_populates="feature_permissions"
    )

class SystemSettings(Base):
    __tablename__ = "system_settings"
    id = Column(Integer, primary_key=True)
    organization_name = Column(String(150), default="AeroGuard AI")
    airport_name = Column(String(150), default="Main Airport")
    language = Column(String(10), default="en")
    timezone = Column(String(50), default="UTC")
    system_name = Column(String(100), default="AeroGuard AI")
    detection_confidence = Column(Float, default=0.5)
    tracking_enabled = Column(Boolean, default=True)
    face_recognition_enabled = Column(Boolean, default=True)
    enable_alert_sounds = Column(Boolean, default=True)
    default_fps = Column(Integer, default=30)
    video_resolution = Column(String(20), default="720p")
    jpeg_quality = Column(Integer, default=70)
    jwt_expiration = Column(Integer, default=60)
    # Performance / AI options
    gpu_enabled = Column(Boolean, default=False)
    frame_skip = Column(Integer, default=0)
    tracker_backend = Column(String(50), default="iou")
    # Phase 7 AI module toggles (system-wide)
    loitering_enabled = Column(Boolean, default=False)
    loitering_seconds = Column(Integer, default=30)
    crowd_density_enabled = Column(Boolean, default=False)
    crowd_density_threshold = Column(Integer, default=10)
    abandoned_bag_enabled = Column(Boolean, default=False)
    abandoned_bag_seconds = Column(Integer, default=60)
    wrong_direction_enabled = Column(Boolean, default=False)
    wrong_direction_angle_threshold = Column(Integer, default=150)
    restricted_area_enabled = Column(Boolean, default=False)
    fire_detection_enabled = Column(Boolean, default=False)
    smoke_detection_enabled = Column(Boolean, default=False)

class Camera(Base):
    __tablename__ = "cameras"
    __table_args__ = (
        UniqueConstraint(
            "camera_id",
            "customer_profile_id",
            name="uq_cameras_id_customer_profile",
        ),
    )
    camera_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    camera_name = Column(String(100), nullable=False)
    location = Column(String(150), nullable=False)
    stream_url = Column(Text, nullable=False)
    camera_type = Column(String(20), default="LIVE") # LIVE, UPLOAD
    status = Column(String(20), default="Offline")
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False, index=True)
    customer_profile_id = Column(
        UUID(as_uuid=True),
        ForeignKey("customer_profiles.customer_profile_id"),
        nullable=True,
        index=True,
    )
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    owner = relationship("User", back_populates="cameras", foreign_keys="Camera.owner_id")
    zones = relationship(
        "RestrictedZone",
        back_populates="camera",
        cascade="all, delete-orphan",
        foreign_keys="RestrictedZone.camera_id",
    )
    detections = relationship(
        "Detection",
        back_populates="camera",
        cascade="all, delete-orphan",
        foreign_keys="Detection.camera_id",
    )
    ai_events = relationship("AIEvent", back_populates="camera", cascade="all, delete-orphan", foreign_keys="AIEvent.camera_id")

class RestrictedZone(Base):
    __tablename__ = "restricted_zones"
    __table_args__ = (
        ForeignKeyConstraint(
            ["camera_id", "customer_profile_id"],
            ["cameras.camera_id", "cameras.customer_profile_id"],
            name="fk_restricted_zones_camera_tenant",
        ),
    )
    zone_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    camera_id = Column(UUID(as_uuid=True), ForeignKey("cameras.camera_id"), nullable=False)
    zone_name = Column(String(100), nullable=False)
    zone_type = Column(String(50), default="Restricted Area")
    polygon_coords = Column(JSONB, nullable=False)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False, index=True)
    customer_profile_id = Column(
        UUID(as_uuid=True),
        ForeignKey("customer_profiles.customer_profile_id"),
        nullable=True,
        index=True,
    )
    tripwire_allowed_group_size = Column(Integer, nullable=True)
    tripwire_initial_occupancy = Column(Integer, nullable=True)
    tripwire_current_occupancy = Column(Integer, nullable=True)
    tripwire_entry_direction = Column(String(20), nullable=True)
    tripwire_requires_confirmation = Column(Boolean, nullable=False, default=False, server_default="false")
    camera = relationship(
        "Camera",
        back_populates="zones",
        foreign_keys=[camera_id],
    )

class Detection(Base):
    __tablename__ = "detections"
    __table_args__ = (
        ForeignKeyConstraint(
            ["camera_id", "customer_profile_id"],
            ["cameras.camera_id", "cameras.customer_profile_id"],
            name="fk_detections_camera_tenant",
        ),
    )
    detection_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    camera_id = Column(UUID(as_uuid=True), ForeignKey("cameras.camera_id"), nullable=False)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False, index=True)
    customer_profile_id = Column(
        UUID(as_uuid=True),
        ForeignKey("customer_profiles.customer_profile_id"),
        nullable=True,
        index=True,
    )
    detection_type = Column(String(50), nullable=False)
    confidence = Column(Float, nullable=False)
    priority = Column(String(20))
    is_violation = Column(Boolean, default=False)
    violation_type = Column(String(50)) # Restricted, Wrong Direction
    detected_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    camera = relationship(
        "Camera",
        back_populates="detections",
        foreign_keys=[camera_id],
    )
    owner = relationship("User", back_populates="detections", foreign_keys="Detection.owner_id")


class EmailVerificationToken(Base):
    __tablename__ = "email_verifications"
    token_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False, index=True)
    token = Column(String(255), nullable=False, unique=True, index=True)
    otp_code = Column(String(20), nullable=True)
    new_email = Column(String(255), nullable=True)
    new_username = Column(String(100), nullable=True)
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)
    attempts = Column(Integer, default=0)
    resend_count = Column(Integer, default=0)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False, index=True)
    token = Column(String(255), nullable=False, unique=True, index=True)
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)
    revoked = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    user_agent = Column(String(500), nullable=True)
    operating_system = Column(String(100), nullable=True)
    browser = Column(String(100), nullable=True)
    device_category = Column(String(50), nullable=True)
    device_type = Column(String(200), nullable=True)
    device_model = Column(String(100), nullable=True)


class ActivityLog(Base):
    __tablename__ = "activity_logs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False, index=True)
    event_type = Column(String(100), nullable=False)
    details = Column(JSONB, nullable=True)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(300), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class UserSettings(Base):
    __tablename__ = "user_settings"
    settings_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False, unique=True, index=True)
    customer_profile_id = Column(
        UUID(as_uuid=True),
        ForeignKey("customer_profiles.customer_profile_id"),
        nullable=True,
        index=True,
    )

    # General
    organization_name = Column(String(150), default="")
    airport_name = Column(String(150), default="")
    system_name = Column(String(100), default="AeroGuard AI")
    language = Column(String(10), default="en")
    timezone = Column(String(50), default="UTC")
    date_format = Column(String(20), default="YYYY-MM-DD")
    time_format = Column(String(20), default="24h")

    # AI Settings
    detection_confidence = Column(Float, default=0.5)
    tracking_enabled = Column(Boolean, default=True)
    object_detection_enabled = Column(Boolean, default=True)
    face_detection_enabled = Column(Boolean, default=False)
    face_recognition_enabled = Column(Boolean, default=False)
    max_objects = Column(Integer, default=10)
    detection_fps = Column(Integer, default=15)

    # Camera Settings
    default_fps = Column(Integer, default=30)
    recording_quality = Column(String(20), default="medium")
    frame_buffer = Column(Integer, default=5)
    auto_reconnect = Column(Boolean, default=True)
    default_camera_resolution = Column(String(20), default="720p")

    # Stream Settings
    stream_video_resolution = Column(String(20), default="720p")
    video_resolution = Column(String(20), default="720p")
    jpeg_quality = Column(Integer, default=75)
    compression = Column(String(50), default="h264")
    compression_enabled = Column(Boolean, default=True)
    bitrate = Column(String(50), default="2000k")

    # Alert Settings
    enable_alert_sounds = Column(Boolean, default=True)
    alert_duration = Column(Integer, default=5)
    alert_volume = Column(Integer, default=80)
    min_alert_confidence = Column(Float, default=0.5)
    show_alert_labels = Column(Boolean, default=True)
    desktop_notifications = Column(Boolean, default=True)

    # Performance / AI options
    gpu_enabled = Column(Boolean, default=False)
    frame_skip = Column(Integer, default=0)

    # Phase 7 AI Module Toggles
    loitering_enabled = Column(Boolean, default=False)
    loitering_seconds = Column(Integer, default=30)

    crowd_density_enabled = Column(Boolean, default=False)
    crowd_density_threshold = Column(Integer, default=10)

    abandoned_bag_enabled = Column(Boolean, default=False)
    abandoned_bag_seconds = Column(Integer, default=60)

    wrong_direction_enabled = Column(Boolean, default=False)
    wrong_direction_angle_threshold = Column(Integer, default=150)

    restricted_area_enabled = Column(Boolean, default=False)

    fire_detection_enabled = Column(Boolean, default=False)
    smoke_detection_enabled = Column(Boolean, default=False)

    # Security Settings
    jwt_expiration = Column(Integer, default=60)
    session_timeout = Column(Integer, default=30)
    password_policy = Column(String(200), default="min:8,upper:1,digit:1")
    remember_me_default = Column(Boolean, default=True)

    # Profile Settings
    theme = Column(String(20), default="light")
    profile_language = Column(String(10), default="en")
    sidebar_state = Column(String(20), default="expanded")
    dashboard_layout = Column(String(50), default="default")
    accent_color = Column(String(20), default="#3b82f6")

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now(), nullable=True)

    

class Report(Base):
    __tablename__ = "reports"
    report_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False, index=True)
    generated_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    customer_profile_id = Column(
        UUID(as_uuid=True),
        ForeignKey("customer_profiles.customer_profile_id"),
        nullable=True,
        index=True,
    )
    generated_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    title = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    report_type = Column(String(50), default="custom")
    filters = Column(JSONB, nullable=True)
    summary = Column(JSONB, nullable=True)
    charts = Column(JSONB, nullable=True)
    details = Column(JSONB, nullable=True)
    export_history = Column(JSONB, nullable=True)  # list of exports with metadata

    owner = relationship("User", back_populates="reports", foreign_keys="Report.owner_id")


class Tracking(Base):
    __tablename__ = "trackings"
    __table_args__ = (
        UniqueConstraint(
            "track_id",
            "customer_profile_id",
            name="uq_trackings_id_customer_profile",
        ),
        ForeignKeyConstraint(
            ["camera_id", "customer_profile_id"],
            ["cameras.camera_id", "cameras.customer_profile_id"],
            name="fk_trackings_camera_tenant",
        ),
    )
    track_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    camera_id = Column(UUID(as_uuid=True), ForeignKey("cameras.camera_id"), nullable=False, index=True)
    customer_profile_id = Column(
        UUID(as_uuid=True),
        ForeignKey("customer_profiles.customer_profile_id"),
        nullable=True,
        index=True,
    )
    track_type = Column(String(50), default="person")
    track_label = Column(String(150), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    last_seen_at = Column(TIMESTAMP(timezone=True), nullable=True)
    latest_bbox = Column(JSONB, nullable=True)
    confidence = Column(Float, nullable=True)


class AIEvent(Base):
    __tablename__ = "ai_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["camera_id", "customer_profile_id"],
            ["cameras.camera_id", "cameras.customer_profile_id"],
            name="fk_ai_events_camera_tenant",
        ),
        ForeignKeyConstraint(
            ["track_id", "customer_profile_id"],
            ["trackings.track_id", "trackings.customer_profile_id"],
            name="fk_ai_events_track_tenant",
        ),
    )
    event_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    track_id = Column(UUID(as_uuid=True), ForeignKey("trackings.track_id"), nullable=True, index=True)
    camera_id = Column(UUID(as_uuid=True), ForeignKey("cameras.camera_id"), nullable=False, index=True)
    detected_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    customer_profile_id = Column(
        UUID(as_uuid=True),
        ForeignKey("customer_profiles.customer_profile_id"),
        nullable=True,
        index=True,
    )
    detection_type = Column(String(100), nullable=False)
    severity = Column(String(20), nullable=False)
    confidence = Column(Float, nullable=True)
    screenshot_path = Column(String(400), nullable=True)
    event_metadata = Column("metadata", JSONB, nullable=True)
    is_read = Column(Boolean, nullable=False, default=False, server_default="false")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    camera = relationship("Camera", back_populates="ai_events", foreign_keys="AIEvent.camera_id")
    owner = relationship("User", back_populates="ai_events", foreign_keys="AIEvent.detected_by")
