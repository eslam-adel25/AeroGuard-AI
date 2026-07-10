# REST API Reference (implementation-derived)

All backend routes are mounted under `/api/v1/` unless noted otherwise. Authentication uses Bearer JWT tokens in the `Authorization` header; the token creation code is in `backend/app/core/security.py`.

Summary of routers and key endpoints found in the codebase:

- `POST /api/v1/auth/register` — Register new user (creates verification token, sends email link if SMTP configured).
- `POST /api/v1/auth/login` — Authenticate user with username/password. Returns `access_token`, `refresh_token`, and `user` metadata.
- `POST /api/v1/auth/refresh` — Exchange a refresh token for a new access token.
- `GET /api/v1/auth/verify?token=...` — Verify an email change / email address (uses EmailVerificationToken).
- `POST /api/v1/auth/resend-verification` — Resend verification email (rate-limited by code logic).
- `POST /api/v1/auth/logout` — Revoke refresh token (expects `refresh_token` in body).

Cameras

- `POST /api/v1/cameras/` — Add a camera. Accepts form fields and optional file upload for `camera_type=UPLOAD` (video file). Enforces extension and size checks.
- `GET /api/v1/cameras/` — List cameras (owner-limited unless Administrator).
- `POST /api/v1/cameras/{camera_id}/start` — Start AI processing for a camera (background task) — ownership check enforced.
- `POST /api/v1/cameras/{camera_id}/zones` — Add restricted zone (ownership enforced).
- `GET /api/v1/cameras/{camera_id}/zones` — List restricted zones (ownership enforced).
- `DELETE /api/v1/cameras/{camera_id}` — Delete a camera and uploaded video file if present (ownership enforced).
- `GET /api/v1/cameras/{camera_id}/stream` — MJPEG streaming endpoint; requires ownership.

Users & Profile

- `GET /api/v1/users/profile` — Get current user profile (token required).
- `PUT /api/v1/users/profile` — Update current user's profile (email/username changes create verification tokens instead of immediate update).
- `PUT|POST /api/v1/users/profile/password` — Change password, revokes refresh tokens on success.
- `POST /api/v1/users/profile/avatar` — Upload avatar; validates extension and size; optional resizing using Pillow if available.
- `GET /api/v1/users/profile/activity` — Returns recent activity (ActivityRepository).
- `GET /api/v1/users/profile/sessions` — List active refresh tokens for current user.
- `POST /api/v1/users/profile/logout-all` — Revoke all refresh tokens.
- Admin-only routes: `GET /api/v1/users/`, `POST /api/v1/users/`, `DELETE /api/v1/users/{user_id}`, `GET /api/v1/users/roles`.

Reports

- `POST /api/v1/reports/generate` — Generate a report for a date range and persist a report record.
- `GET /api/v1/reports/` — List generated reports (owner-limited unless Administrator).
- `GET /api/v1/reports/{report_id}` — Get report detail and contents.
- `GET /api/v1/reports/export/csv?report_id=...` — Export report as CSV; report ownership enforced.
- `GET /api/v1/reports/export/excel?report_id=...` — Export report as Excel (requires openpyxl available on server).
- `GET /api/v1/reports/export/pdf?report_id=...` — Export report as PDF.
- `DELETE /api/v1/reports/{report_id}` — Delete persisted report (owner-limited unless Administrator).
- `GET /api/v1/reports/summary` and `/api/v1/reports/dashboard` — Return aggregated analytics used by the frontend dashboard.

AI Events

- `GET /api/v1/ai/events` — List AI events; admin or owner-limited when `camera_id` specified.
- `GET /api/v1/ai/events/{event_id}` — Get AI event detail (ownership enforced for non-admins).
- `GET /api/v1/ai/events/{event_id}/screenshot` — Download stored screenshot for event (ownership enforced).
- `POST /api/v1/ai/events/manual` — Manually create AI event (accepts UploadFile screenshot optionally).

WebSocket

- `ws://<host>/ws/dashboard?token=<ACCESS_TOKEN>` — WebSocket endpoint for live `ai_event`, `new_alert`, `ai_status` and `camera_status` broadcasts. The frontend constructs the URL including `token` as query parameter.

Authentication / Rate limiting notes

- Passwords hashed using `bcrypt` (`backend/app/core/security.py`).
- JWT creation/verification lives in `backend/app/core/security.py`; token expiry controlled by `ACCESS_TOKEN_EXPIRE_MINUTES` env var (defaults to 60 minutes).
- The auth router includes an in-memory throttling mechanism (login/register attempt buckets) implemented in `backend/app/api/v1/auth.py` to reduce brute-force attempts.

Example: login request

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"SecretPass123"}'
```

Response (example)

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "refresh_token": "<refresh-token>",
  "user": {
    "user_id": "...",
    "full_name": "Alice",
    "username": "alice",
    "role": "Officer"
  }
}
```

Notes and omissions

- Full OpenAPI examples and detailed JSON schemas are available if you run the backend and access `/docs` (FastAPI OpenAPI UI).
- This reference is strictly implementation-derived; if you need example payloads for every endpoint, I can generate them next by reading each route's Pydantic schema and creating curl examples.
