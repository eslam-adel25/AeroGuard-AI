# Reference: Key Files and Responsibilities

This quick reference maps important files to the responsibilities they implement in the current workspace.

- backend/app/main.py — application entry point that creates the schema, mounts uploads, and wires the routers.
- backend/app/core/security.py — JWT creation/verification and password hashing.
- backend/app/core/auth_middleware.py — authentication dependency and role access checks.
- backend/app/core/emailer.py — SMTP verification email delivery helper.
- backend/app/database/session.py — SQLAlchemy engine and DB session dependency.
- backend/app/models/models.py — SQLAlchemy ORM models for users, cameras, reports, settings, AI events, and tracking state.
- backend/app/schemas/schemas.py — Pydantic schemas used by the API.
- backend/app/api/v1/auth.py — registration, login, refresh, verification, and logout flows.
- backend/app/api/v1/cameras.py — camera CRUD, zone management, streaming, and AI start/stop routes.
- backend/app/api/v1/users.py — profile updates, avatar upload, password changes, and user management.
- backend/app/api/v1/reports.py — report generation, listing, and export endpoints.
- backend/app/api/v1/settings.py — user settings CRUD and AI config reloads.
- backend/app/api/v1/ai.py — AI event listing and manual event creation.
- backend/app/api/v1/websocket_api.py — WebSocket dashboard endpoint.
- backend/app/ai/processor.py — YOLOv8 processing loop and heuristic engine.
- backend/app/ai/tracker.py — tracker facade and tracking logic.
- backend/app/services/ai_service.py — AI event persistence and WebSocket broadcast.
- backend/app/services/report_service.py — report aggregation and report generation orchestration.
- backend/app/utils/report_generator.py — export generation helpers for PDF/Excel/CSV-like output.
- frontend/src/services/api.ts — centralized Axios client for the frontend.
- frontend/src/services/socket.ts — WebSocket connection helper and event typing.
