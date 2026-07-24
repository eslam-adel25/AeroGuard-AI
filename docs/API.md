# REST API Reference

All backend routes are mounted under /api/v1 unless noted otherwise. Authentication uses Bearer JWTs in the Authorization header, and the backend exposes the OpenAPI docs at /docs when the server is running.

Authentication

- POST /api/v1/auth/register — creates a user, hashes the password, and optionally sends a verification email.
- POST /api/v1/auth/login — authenticates a user and returns access/refresh tokens plus user metadata.
- POST /api/v1/auth/refresh — exchanges a refresh token for a new access token.
- GET /api/v1/auth/verify — verifies a token sent during registration or email change flows.
- POST /api/v1/auth/resend-verification — reissues verification email data.
- POST /api/v1/auth/logout — revokes a refresh token.
- POST /api/v1/auth/verify-otp — verifies a six-digit email code.

Cameras

- POST /api/v1/cameras/ — creates a camera record and accepts form data for LIVE, USB, or UPLOAD sources.
- GET /api/v1/cameras/ — lists cameras, scoped by ownership unless the caller is an Administrator.
- POST /api/v1/cameras/{camera_id}/start — starts AI processing for a camera in the background.
- POST /api/v1/cameras/{camera_id}/stop — stops AI processing for a camera.
- POST /api/v1/cameras/{camera_id}/zones — adds a restricted zone.
- GET /api/v1/cameras/{camera_id}/zones — lists restricted zones.
- DELETE /api/v1/cameras/{camera_id} — deletes a camera and related records.
- GET /api/v1/cameras/{camera_id}/stream — streams annotated MJPEG frames.

Users and profile

- GET /api/v1/users/profile — returns the current user profile.
- PUT /api/v1/users/profile — updates profile details.
- POST /api/v1/users/profile/password — changes the password and revokes existing refresh tokens.
- POST /api/v1/users/profile/avatar — uploads an avatar.
- GET /api/v1/users/profile/activity — returns recent activity history.
- GET /api/v1/users/profile/sessions — lists current sessions.
- POST /api/v1/users/profile/logout-all — revokes all refresh tokens for the current user.
- Admin-only endpoints exist under /api/v1/users for user management and role lookup.

Reports

- GET /api/v1/reports/summary — returns a summary payload for a requested date range.
- GET /api/v1/reports/dashboard — returns analytics payload used by the dashboard.
- POST /api/v1/reports/generate — generates and stores a report.
- GET /api/v1/reports/ — lists persisted reports.
- GET /api/v1/reports/{report_id} — retrieves report contents and metadata.
- GET /api/v1/reports/export/csv — exports a report as CSV.
- GET /api/v1/reports/export/excel — exports a report as Excel when openpyxl is installed.
- GET /api/v1/reports/export/pdf — exports a report as PDF.
- DELETE /api/v1/reports/{report_id} — deletes a persisted report.

AI events

- GET /api/v1/ai/events — lists AI events.
- GET /api/v1/ai/events/{event_id} — fetches one event.
- GET /api/v1/ai/events/{event_id}/screenshot — returns the stored screenshot.
- POST /api/v1/ai/events/manual — manually creates an AI event.

Realtime notifications

- WebSocket endpoint: ws://<host>/ws/dashboard?token=<ACCESS_TOKEN>
- The frontend uses this endpoint to receive ai_event, new_alert, ai_status, alarm_state, and camera_status messages.

Implementation notes

- Passwords are hashed with bcrypt in backend/app/core/security.py.
- JWT verification and refresh-token storage are implemented server-side.
- Authentication endpoints use an in-memory rate-limit bucket per client and per username.
