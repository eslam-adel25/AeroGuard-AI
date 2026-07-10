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

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True

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

    class Config:
        from_attributes = True


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
    organization_name: Optional[str] = None
    airport_name: Optional[str] = None
    language: Optional[str] = None
    timezone: Optional[str] = None
    system_name: Optional[str] = None
    detection_confidence: Optional[float] = None
    tracking_enabled: Optional[bool] = None
    object_detection_enabled: Optional[bool] = None
    face_detection_enabled: Optional[bool] = None
    face_recognition_enabled: Optional[bool] = None
    max_objects: Optional[int] = None
    enable_alert_sounds: Optional[bool] = None
    alert_duration: Optional[int] = None
    min_alert_confidence: Optional[float] = None
    show_alert_labels: Optional[bool] = None
    default_fps: Optional[int] = None
    video_resolution: Optional[str] = None
    jpeg_quality: Optional[int] = None
    jwt_expiration: Optional[int] = None
    session_timeout: Optional[int] = None
    # Profile
    theme: Optional[str] = None
    profile_language: Optional[str] = None
    sidebar_state: Optional[str] = None
    dashboard_layout: Optional[str] = None
    accent_color: Optional[str] = None

class SettingsResponse(SettingsUpdate):
    settings_id: Optional[UUID] = None
    owner_id: Optional[UUID] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ZoneCreate(BaseModel):
    zone_name: str
    zone_type: str
    polygon_coords: List[List[int]]

    class Config:
        from_attributes = True

# قالب لبيانات الـ FPS القادمة من الـ AI
class AIStatusUpdate(BaseModel):
    fps: int