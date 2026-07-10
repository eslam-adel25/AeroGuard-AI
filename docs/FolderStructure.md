# Folder Structure (repository view)

This is the repository layout as observed when inspecting the source. Paths are workspace-relative.

- `README.md` — repository index and docs links.
- `docs/` — this documentation folder.
- `awro-guard/backend/` — FastAPI backend and AI engine implementation
  - `app/`
    - `api/v1/` — REST API routers (`auth.py`, `cameras.py`, `users.py`, `reports.py`, `settings.py`, `ai.py`, `websocket_api.py`)
    - `ai/` — AI engine and tracker adapters (`processor.py`, `tracker.py`, `bytetrack_adapter.py`, `deepsort_adapter.py`)
    - `core/` — security, emailer, auth middleware (`security.py`, `emailer.py`, `auth_middleware.py`)
    - `database/` — SQLAlchemy session and engine (`session.py`)
    - `models/` — SQLAlchemy models and model files (`models.py`, `yolov8n.pt`)
    - `repositories/` — DB access wrappers for each aggregate
    - `schemas/` — Pydantic request/response models (`schemas.py`)
    - `services/` — business logic and AI/report helpers (`ai_service.py`, `report_service.py`, `decision_engine.py`, `camera_service.py`, `auth_service.py`)
    - `utils/` — helpers (report_generator.py)
    - `websocket/` — connection manager (`manager.py`)
  - `uploads/` — runtime storage for avatars, videos, reports, ai_events
  - `tests/` — unit tests (small set: `test_security_helpers.py`)

- `awro-guard/frontend/` — React + TypeScript SPA built with Vite
  - `src/`
    - `pages/` — main views (`Login.tsx`, `Dashboard.tsx`, `Cameras.tsx`, `Reports.tsx`, `Settings.tsx`, etc.)
    - `components/` — shared UI components
    - `services/` — `api.ts` (Axios client), `socket.ts`, `notificationService.ts`
    - `i18n/` — translations and language provider
  - `package.json`, `vite.config.ts`, `tsconfig.json`

Notes

- There are two copies of `yolov8n.pt` in the repository (`awro-guard/backend/models/` and `awro-guard/backend/app/models/`). The engine references `models/yolov8n.pt` relative to the backend root.
- No Dockerfile is provided. The backend includes a pinned `requirements.txt` at `awro-guard/backend/requirements.txt`.
