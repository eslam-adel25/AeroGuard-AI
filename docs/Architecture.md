# System Architecture

This document describes the architecture implemented in the current repository.

Repository layout

- backend/ — FastAPI application, SQLAlchemy models, AI pipeline, and upload storage.
- frontend/ — React + TypeScript single-page application built with Vite.

Primary runtime components

- Camera sources: live RTSP/HTTP streams, USB/webcam devices, and uploaded video files.
- AI engine: backend/app/ai/processor.py runs object detection, tracking, and heuristic evaluation using YOLOv8 and OpenCV.
- Decision engine: backend/app/services/decision_engine.py turns detections into alert-worthy events.
- Backend API: backend/app/api/v1 hosts the REST routers for authentication, cameras, users, reports, settings, AI events, and WebSocket support.
- Persistence layer: SQLAlchemy models in backend/app/models/models.py are created on startup and backed by the DATABASE_URL connection string.
- Realtime layer: backend/app/websocket/manager.py handles live dashboard events.
- Frontend: frontend/src contains the dashboard UI, camera management, reports, settings, profile pages, and the API/WebSocket services.

Request flow

1. The camera router accepts a camera definition and stores its stream source.
2. The AI processor reads frames from that source, runs inference, and tracks objects across frames.
3. The decision engine decides whether an event should be created.
4. The AI service persists the event, saves screenshots when needed, and broadcasts the result to the dashboard.
5. The React frontend receives the event and updates the UI in real time.

Implementation notes

- The app entry point is backend/app/main.py. On startup it creates the database schema and registers the AI processor with the settings API.
- Static uploads are served under /uploads from backend/uploads.
- Security headers and a local development CORS allowlist are applied in backend/app/main.py.

Current limitations

- The repository does not include containerization files such as Dockerfile or docker-compose.yml.
- Environment variables are expected to be provided through the runtime environment or a local .env file.
