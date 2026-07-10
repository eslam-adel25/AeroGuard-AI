# Reference: Key files and responsibilities

This quick reference maps important files to their responsibilities. Use this to quickly find implementation points.

- `awro-guard/backend/app/main.py` — application entry: creates DB schema, registers routers, sets security headers and CORS.
- `awro-guard/backend/app/core/security.py` — JWT creation/verification, bcrypt password hashing, `get_current_user` dependency.
- `awro-guard/backend/app/core/auth_middleware.py` — header-based token extraction and `role_required` decorator.
- `awro-guard/backend/app/core/emailer.py` — SMTP-based verification email sender.
- `awro-guard/backend/app/database/session.py` — SQLAlchemy engine and `get_db()` dependency.
- `awro-guard/backend/app/models/models.py` — SQLAlchemy ORM models and AI model file locations.
- `awro-guard/backend/app/schemas/schemas.py` — Pydantic models used by API.
- `awro-guard/backend/app/api/v1/auth.py` — registration, login, refresh, verify, resend, logout.
- `awro-guard/backend/app/api/v1/cameras.py` — camera CRUD, zone management, stream endpoint, start analysis.
- `awro-guard/backend/app/api/v1/users.py` — user profile, avatar upload, password change, admin user management.
- `awro-guard/backend/app/api/v1/reports.py` — reports generation, listing, exports.
- `awro-guard/backend/app/api/v1/settings.py` — user settings CRUD.
- `awro-guard/backend/app/api/v1/ai.py` — AI events listing, manual event creation, screenshot download.
- `awro-guard/backend/app/api/v1/websocket_api.py` — WebSocket endpoint for dashboard notifications.
- `awro-guard/backend/app/ai/processor.py` — YOLOv8-based processing loop and real-time heuristics.
- `awro-guard/backend/app/ai/tracker.py` — tracking implementations and `TrackerManager` facade.
- `awro-guard/backend/app/services/ai_service.py` — persists AI events and broadcasts via WebSocket.
- `awro-guard/backend/app/services/report_service.py` — report aggregation and generation orchestration.
- `awro-guard/backend/app/utils/report_generator.py` — PDF/Excel generators for exported reports.
- `awro-guard/frontend/src/services/api.ts` — centralized Axios client and all frontend API calls.
- `awro-guard/frontend/src/services/socket.ts` — WebSocket connection helper and message types used by the frontend.
