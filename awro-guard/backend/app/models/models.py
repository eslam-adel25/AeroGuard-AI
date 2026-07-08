import uuid
from sqlalchemy import Column, String, ForeignKey, TIMESTAMP, Text, Float, Integer, Boolean, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database.session import Base

class Role(Base):
    __tablename__ = "roles"
    role_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role_name = Column(String(50), nullable=False, unique=True)
    users = relationship("User", back_populates="role")

class User(Base):
    __tablename__ = "users"
    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.role_id"))
    full_name = Column(String(150), nullable=False)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(Text, nullable=False)
    phone = Column(String(20))
    organization = Column(String(150))
    profile_picture = Column(Text)
    status = Column(String(20), default="Active")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    
    role = relationship("Role", back_populates="users")

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

class Camera(Base):
    __tablename__ = "cameras"
    camera_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    camera_name = Column(String(100), nullable=False)
    location = Column(String(150), nullable=False)
    stream_url = Column(Text, nullable=False)
    camera_type = Column(String(20), default="LIVE") # LIVE, UPLOAD
    status = Column(String(20), default="Offline")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    zones = relationship("RestrictedZone", back_populates="camera", cascade="all, delete-orphan")
    detections = relationship("Detection", back_populates="camera")

class RestrictedZone(Base):
    __tablename__ = "restricted_zones"
    zone_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    camera_id = Column(UUID(as_uuid=True), ForeignKey("cameras.camera_id"), nullable=False)
    zone_name = Column(String(100), nullable=False)
    zone_type = Column(String(50), default="Restricted Area")
    polygon_coords = Column(JSONB, nullable=False)
    camera = relationship("Camera", back_populates="zones")

class Detection(Base):
    __tablename__ = "detections"
    detection_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    camera_id = Column(UUID(as_uuid=True), ForeignKey("cameras.camera_id"), nullable=False)
    detection_type = Column(String(50), nullable=False)
    confidence = Column(Float, nullable=False)
    priority = Column(String(20))
    is_violation = Column(Boolean, default=False)
    violation_type = Column(String(50)) # Restricted, Wrong Direction
    detected_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    camera = relationship("Camera", back_populates="detections")