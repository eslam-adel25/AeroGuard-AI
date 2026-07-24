# Folder Structure

This is the repository layout observed in the workspace.

- README.md — repository landing page and project overview.
- docs/ — implementation-focused documentation set.
- backend/ — FastAPI backend, AI engine, database models, and upload storage.
  - app/ — application package.
    - api/v1/ — REST routers for auth, cameras, users, reports, settings, AI events, and WebSocket.
    - ai/ — AI processor, tracker facade, and tracker adapters.
    - core/ — security helpers, emailer, and auth middleware.
    - database/ — SQLAlchemy engine and session helpers.
    - models/ — SQLAlchemy models and model weights.
    - repositories/ — persistence access layers.
    - schemas/ — Pydantic request/response models.
    - services/ — business logic for AI, reports, auth, cameras, and decisions.
    - utils/ — helper modules for reports and device info.
    - websocket/ — WebSocket connection manager.
  - uploads/ — runtime files for avatars, videos, screenshots, and reports.
  - tests/ — backend test suite.
- frontend/ — Vite + React + TypeScript frontend.
  - src/ — application pages, components, services, and localization files.
  - public/ — static assets such as sounds.
  - package.json, vite.config.ts, tsconfig files — frontend build configuration.

Notes

- The repository contains model weight files under backend/models and backend/app/models, and the AI processor resolves them relative to the backend root.
- There is currently no containerization configuration in the repo.
