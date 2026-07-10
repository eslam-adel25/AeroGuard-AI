# Reference: Key files and responsibilities

This quick reference maps important files to their responsibilities. Use this to quickly find implementation points.

- `backend/app/main.py` — application entry: creates DB schema, registers routers, sets security headers and CORS.
- `backend/app/core/security.py` — JWT creation/verification, bcrypt password hashing, `get_current_user` dependency.
- `backend/app/core/auth_middleware.py` — header-based token extraction and `role_required` decorator.
- `backend/app/core/emailer.py` — SMTP-based verification email sender.
- `backend/app/database/session.py` — SQLAlchemy engine and `get_db()` dependency.
- `backend/app/models/models.py` — SQLAlchemy ORM models and AI model file locations.
- `backend/app/schemas/schemas.py` — Pydantic models used by API.
- `backend/app/api/v1/auth.py` — registration, login, refresh, verify, resend, logout.
- `backend/app/api/v1/cameras.py` — camera CRUD, zone management, stream endpoint, start analysis.
- `backend/app/api/v1/users.py` — user profile, avatar upload, password change, admin user management.
- `backend/app/api/v1/reports.py` — reports generation, listing, exports.
- `backend/app/api/v1/settings.py` — user settings CRUD.
- `backend/app/api/v1/ai.py` — AI events listing, manual event creation, screenshot download.
- `backend/app/api/v1/websocket_api.py` — WebSocket endpoint for dashboard notifications.
- `backend/app/ai/processor.py` — YOLOv8-based processing loop and real-time heuristics.
- `backend/app/ai/tracker.py` — tracking implementations and `TrackerManager` facade.
- `backend/app/services/ai_service.py` — persists AI events and broadcasts via WebSocket.
- `backend/app/services/report_service.py` — report aggregation and generation orchestration.
- `backend/app/utils/report_generator.py` — PDF/Excel generators for exported reports.
- `frontend/src/services/api.ts` — centralized Axios client and all frontend API calls.
- `frontend/src/services/socket.ts` — WebSocket connection helper and message types used by the frontend.
