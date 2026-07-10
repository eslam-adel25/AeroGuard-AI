# Settings System

The application exposes system- and user-level settings used to control AI behavior, UI preferences, and security defaults.

Models

- `SystemSettings` (`backend/app/models/models.py`) — global system defaults (detection confidence, tracker backend, AI toggles like `loitering_enabled`, GPU flag, `jwt_expiration`).
- `UserSettings` — per-user settings stored in `user_settings` table (language, theme, AI per-user overrides, alert preferences).

API

- `GET /api/v1/settings/` — returns the current user's `UserSettings` (created with defaults on first access).
- `PUT /api/v1/settings/` — update user settings.
- `POST /api/v1/settings/reset` — reset a user's settings to defaults.

Implementation notes

- `AIProcessor.update_config(settings_model)` uses `SystemSettings` values to reload model and adjust pipeline thresholds.
- The frontend `ISystemSettings` interface in `frontend/src/services/api.ts` mirrors many fields from `UserSettings`/`SystemSettings`.
