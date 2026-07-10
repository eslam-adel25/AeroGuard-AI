# Database Schema & Models (implementation-derived)

This file summarizes the SQLAlchemy models implemented in `awro-guard/backend/app/models/models.py`. The repository uses PostgreSQL-specific column types (UUID, JSONB).

Important tables and key fields

- `roles`
  - `role_id` (UUID, PK)
  - `role_name` (string)

- `users`
  - `user_id` (UUID, PK)
  - `role_id` (FK -> roles.role_id)
  - `full_name`, `username`, `email`
  - `password_hash` (stored as text, bcrypt)
  - `profile_picture` (path)
  - `status` (e.g., Pending, Active)
  - `is_verified` (bool)
  - `last_login`, `created_at`, `updated_at`

- `system_settings`
  - global settings like `organization_name`, `detection_confidence`, `tracking_enabled`, `jwt_expiration`, `gpu_enabled`, etc.

- `cameras`
  - `camera_id` (UUID, PK)
  - `camera_name`, `location`, `stream_url`
  - `camera_type` (LIVE, UPLOAD, USB)
  - `owner_id` (FK -> users.user_id)
  - `status`, `created_at`

- `restricted_zones`
  - `zone_id` (UUID, PK)
  - `camera_id` (FK -> cameras.camera_id)
  - `zone_name`, `zone_type`
  - `polygon_coords` (JSONB)
  - `owner_id` (FK -> users.user_id)

- `detections`
  - `detection_id` (UUID)
  - `camera_id` (FK)
  - `owner_id` (FK -> users.user_id)
  - `detection_type`, `confidence`, `priority`, `is_violation`, `violation_type`, `detected_at`

- `email_verifications`
  - tokens for email/username change flows: `token_id`, `user_id`, `token`, `new_email`, `new_username`, `expires_at`, `resend_count`, `attempts`

- `refresh_tokens`
  - `id`, `user_id`, `token`, `expires_at`, `revoked`

- `activity_logs`
  - `id`, `user_id`, `event_type`, `details` (JSONB), `ip_address`, `user_agent`, `created_at`

- `user_settings`
  - per-user settings persisted as model fields (language, timezone, frame_buffer, etc.)

- `reports`
  - `report_id` (UUID), `owner_id`, `generated_by`, `generated_at`, `title`, `description`, `report_type`, `filters` (JSONB), `summary` (JSONB), `details` (JSONB), `export_history` (JSONB)

- `trackings`
  - used by the tracking system (track_id, camera_id, track_type, track_label, latest_bbox, confidence, timestamps)

- `ai_events`
  - `event_id` (UUID), `track_id` (FK optional), `camera_id`, `detected_by` (user), `detection_type`, `severity`, `confidence`, `screenshot_path`, `metadata` (JSONB), `created_at`

Relationships

- `users` ← 1:N → `cameras` (owner_id)
- `cameras` ← 1:N → `detections`
- `users` ← 1:N → `refresh_tokens`
- AI events reference cameras and optionally `users.detected_by`.

Notes

- The code uses PostgreSQL `JSONB` and `UUID` dialect types, so `DATABASE_URL` should point to a PostgreSQL instance (e.g. `postgresql+psycopg2://user:pass@host/dbname`).
- Nothing in the repo suggests use of Alembic migrations — database schema is created on startup via `Base.metadata.create_all(bind=engine)` in `awro-guard/backend/app/main.py`.

Refer to the SQLAlchemy models in `awro-guard/backend/app/models/models.py` for full schema details.
