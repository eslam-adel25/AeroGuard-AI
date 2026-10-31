# Settings System

The application exposes system-level and user-level settings that influence the AI engine, dashboard experience, and security defaults.

Models

- SystemSettings in backend/app/models/models.py stores global defaults such as detection confidence, tracker backend, GPU usage, and AI-rule toggles.
- UserSettings in backend/app/models/models.py stores per-user preferences including language, theme, alert behavior, and AI thresholds.

API

- GET /api/v1/settings/ returns the current user’s settings, creating defaults if they do not yet exist.
- PUT /api/v1/settings/ updates the current user’s settings and notifies the running AI processor.
- POST /api/v1/settings/reset restores the user’s settings to defaults.

Implementation notes

- The settings API updates the running AI processor through the registered processor instance in backend/app/api/v1/settings.py.
- The frontend service layer mirrors many of the same fields in frontend/src/services/api.ts.
- A disabled SystemSettings AI-module toggle overrides the matching
  UserSettings toggle when the processor settings snapshot is built. A global
  enabled value does not enable a module that the customer disabled.
- Updating or resetting user settings preserves the stored
  abandoned_bag_seconds value; a missing legacy value uses the 60-second
  runtime fallback.

SystemSettings currently has no management API or UI. The processor reads the
global row when it creates a customer's in-memory settings snapshot and when
that customer's settings are explicitly reloaded. Direct database changes do
not notify the processor, so existing snapshots remain in effect until a
customer settings reload or processor restart.
