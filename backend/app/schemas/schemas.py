from pydantic import BaseModel, EmailStr
from typing import Optional, List
from uuid import UUID
from datetime import datetime

# ==========================================
# 1. قوالب الكاميرات (Section 5)
# ==========================================

class CameraCreate(BaseModel):
    camera_name: str
    location: str
    stream_url: str
    camera_type: str  # LIVE, UPLOAD, USB

class CameraResponse(CameraCreate):
    camera_id: UUID
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ==========================================
# 2. قوالب المستخدمين والهوية (Section 1 & 3)
# ==========================================

# يستخدم عند تسجيل مستخدم جديد لنفسه (بدون تحديد Role)
class UserRegister(BaseModel):
    full_name: str
    username: str
    email: EmailStr
    password: str
    phone: str
    organization: Optional[str] = None

# يستخدم بواسطة الأدمن لإنشاء موظفين وتحديد رتبهم (حل مشكلة ImportError)
class UserCreate(UserRegister):
    role_id: UUID

class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    refresh_token: str | None = None


class RefreshRequest(BaseModel):
    refresh_token: str


class ResendVerificationRequest(BaseModel):
    email: str

class RoleResponse(BaseModel):
    role_id: UUID
    role_name: str

    model_config = {"from_attributes": True}

class UserResponse(BaseModel):
    user_id: UUID
    full_name: str
    username: str
    email: str
    phone: Optional[str] = None
    organization: Optional[str] = None
    profile_picture: Optional[str] = None
    status: str
    role_id: UUID
    role: Optional[RoleResponse] = None
    creator_name: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    organization: Optional[str] = None


class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str


# ==========================================
# 3. قوالب الإعدادات والمناطق (Section 2 & 7)
# ==========================================

class SettingsUpdate(BaseModel):
    # General Settings
    organization_name: Optional[str] = None
    airport_name: Optional[str] = None
    language: Optional[str] = None
    timezone: Optional[str] = None
    system_name: Optional[str] = None
    
    # AI Core Settings
    detection_confidence: Optional[float] = None
    tracking_enabled: Optional[bool] = None
    object_detection_enabled: Optional[bool] = None
    face_detection_enabled: Optional[bool] = None
    face_recognition_enabled: Optional[bool] = None
    max_objects: Optional[int] = None
    
    # Camera & Stream Settings
    default_fps: Optional[int] = None
    recording_quality: Optional[str] = None
    frame_buffer: Optional[int] = None
    auto_reconnect: Optional[bool] = None
    video_resolution: Optional[str] = None
    compression_enabled: Optional[bool] = None
    jpeg_quality: Optional[int] = None
    
    # Alert Settings
    enable_alert_sounds: Optional[bool] = None
    alert_duration: Optional[int] = None
    min_alert_confidence: Optional[float] = None
    show_alert_labels: Optional[bool] = None
    
    # Performance / AI Options
    gpu_enabled: Optional[bool] = None
    frame_skip: Optional[int] = None
    
    # Phase 7 AI Module Toggles
    loitering_enabled: Optional[bool] = None
    loitering_seconds: Optional[int] = None
    crowd_density_enabled: Optional[bool] = None
    crowd_density_threshold: Optional[int] = None
    abandoned_bag_enabled: Optional[bool] = None
    abandoned_bag_seconds: Optional[int] = None
    wrong_direction_enabled: Optional[bool] = None
    wrong_direction_angle_threshold: Optional[int] = None
    restricted_area_enabled: Optional[bool] = None
    fire_detection_enabled: Optional[bool] = None
    smoke_detection_enabled: Optional[bool] = None
    
    # Security Settings
    jwt_expiration: Optional[int] = None
    session_timeout: Optional[int] = None

class SettingsResponse(SettingsUpdate):
    settings_id: Optional[UUID] = None
    owner_id: Optional[UUID] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

class ZoneCreate(BaseModel):
    zone_name: str
    zone_type: str
    polygon_coords: List[List[float]]
    video_width: Optional[int] = None
    video_height: Optional[int] = None

    model_config = {"from_attributes": True}

class ZoneResponse(BaseModel):
    zone_id: UUID
    zone_name: str
    zone_type: str
    polygon_coords: List[List[float]]
    video_width: Optional[int] = None
    video_height: Optional[int] = None

    model_config = {"from_attributes": True}

# قالب لبيانات الـ FPS القادمة من الـ AI
class AIStatusUpdate(BaseModel):
    fps: int