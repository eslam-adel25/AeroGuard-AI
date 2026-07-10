# System Architecture & Overview

This document describes the architecture and high-level components of the AeroGuard AI repository as implemented in this codebase.

Repository layout (root)

- `awro-guard/backend/` — FastAPI application and AI engine.
- `awro-guard/frontend/` — React + TypeScript single page application (Vite).

High-level components

- Camera sources: live RTSP/HTTP feeds or uploaded video files.
- AI Engine (`awro-guard/backend/app/ai`) — YOLOv8-based inference pipeline with tracking, heuristics, and event generation.
- Decision Engine (`awro-guard/backend/app/services/decision_engine.py`) — applies business rules (loitering, abandoned bag, restricted-zones, wrong-direction) to detection/track outputs.
- Backend API (`awro-guard/backend/app/api/v1`) — REST endpoints for authentication, cameras, users, settings, reports, AI events, and WebSocket endpoint for live notifications.
- WebSocket manager (`awro-guard/backend/app/websocket/manager.py`) — connection management and broadcast helper used by AI engine and services.
- Persistence — SQLAlchemy models in `awro-guard/backend/app/models/models.py` with PostgreSQL types (UUID, JSONB). Session provided by `awro-guard/backend/app/database/session.py`.
- Reporting & exports — CSV, Excel and PDF generation using `awro-guard/backend/app/utils/report_generator.py` and `awro-guard/backend/app/services/report_service.py`.
- Frontend — dashboard, camera controls, reports, settings, profile, and i18n support in `awro-guard/frontend/src/`.

Data flow (simplified)

1. Camera frames are read by `AIProcessor` (OpenCV) and sent through YOLOv8 for detection.
2. `TrackerManager` (tracker adapters) associates detections across frames.
3. `DecisionEngine` evaluates trackers against configured detection rules (loitering, restricted zone, abandoned bag, wrong direction, fire/smoke) and triggers alerts.
4. `AIService` persists AI events, optionally stores screenshots to `uploads/ai_events`, and pushes notifications via `websocket.manager.broadcast()`.
5. Frontend receives events over WebSocket (`/ws/dashboard`) and displays alerts on the React dashboard.

Notes from the source code

- The engine is initialized in `awro-guard/backend/app/ai/processor.py` as `AIProcessor(model_path="models/yolov8n.pt")`.
- Upload directories exist under `awro-guard/backend/uploads/` for avatars, videos, ai_events, and reports.
- Security middleware in `awro-guard/backend/app/main.py` sets secure headers and an explicit CORS allowlist (localhost development origins).

Limitations observed

- No containerization (Dockerfile) provided in the repo.
- Environment variables are read via `python-dotenv` when present; a `.env` file is not included.

Next: refer to `docs/API.md` for REST endpoints and `docs/AI.md` for AI pipeline details.
