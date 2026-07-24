# AeroGuard AI

> Intelligent surveillance operations platform for monitoring critical infrastructure, public spaces, and secure facilities with AI-assisted detection, real-time alerts, and reporting.

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.95%2B-009688)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19-61DAFB)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-8-646CFF)](https://vitejs.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Required-336791)](https://www.postgresql.org/)
[![YOLOv8](https://img.shields.io/badge/AI-YOLOv8-00A67E)](https://ultralytics.com/)

Developer: Eslam Adel

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [System Architecture](#system-architecture)
- [Tech Stack](#tech-stack)
- [Project Folder Structure](#project-folder-structure)
- [File Responsibilities](#file-responsibilities)
- [Installation](#installation)
- [Running the Project](#running-the-project)
- [Available Scripts](#available-scripts)
- [Environment Variables](#environment-variables)
- [API Overview](#api-overview)
- [Database](#database)
- [AI Pipeline](#ai-pipeline)
- [Localization](#localization)
- [Security](#security)
- [Notifications](#notifications)
- [Reports](#reports)
- [Analytics](#analytics)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)
- [Contributing](#contributing)
- [License](#license)
- [Author](#author)
- [Acknowledgements](#acknowledgements)

---

## Overview

AeroGuard AI is a full-stack surveillance platform composed of a FastAPI backend and a React + TypeScript frontend. The application is designed for operators who need to manage cameras, review live AI detections, inspect alert history, and generate operational reports from one place.

The system currently implements:

- camera registration for live streams, USB devices, and uploaded videos
- AI-assisted object detection and tracking using YOLOv8
- alert generation for restricted zones, wrong-direction motion, loitering, abandoned-bag scenarios, smoke/fire-related events, and other detections
- real-time WebSocket updates for dashboard and alerting workflows
- role-based access for administrators and regular users
- report generation and export to CSV, Excel, and PDF

This project is intended for security operations teams, infrastructure monitoring, and controlled environments where operators need rapid visibility into suspicious activity.

---

## Features

### 1. Multi-source camera operations

The backend accepts camera definitions from:

- live RTSP/HTTP streams
- USB/Webcam sources using the special `0` device path
- uploaded video files

Camera registration and lifecycle control are exposed through the REST API and the dashboard UI.

### 2. AI-powered monitoring

The backend runs an AI processor that loads a YOLO model and analyzes incoming frames. The implementation supports:

- person detection
- bag/backpack/suitcase detection
- vehicle detection
- fire and smoke detection
- object tracking across frames
- overlay labeling and visualization on processed frames

### 3. Security heuristics and alerting

The detection pipeline includes rule-based logic for:

- restricted-area violations
- wrong-direction movement
- loitering
- abandoned-bag ownership tracking
- critical threat classification for weapon/fire/smoke-like indicators

### 4. Real-time notifications

Live alerts are pushed to the frontend over a WebSocket endpoint and surfaced through the dashboard and notification center. The backend also persists AI events for later inspection.

### 5. Role-based access and profile management

The system uses JWT-based authentication, refresh-token handling, and role checks. Admin users can manage other users; standard users can manage their own cameras, profile, and activity.

### 6. Reporting and analytics

Operators can request summary analytics for a date range, inspect recent detections, and export reports in CSV, Excel, and PDF formats.

### 7. Multilingual UI

The frontend provides English and Arabic translations through i18next.

---

## System Architecture

AeroGuard AI follows a layered architecture with clear separation between the UI, API, business services, persistence, and AI engine.

### Frontend

The frontend is a Vite-powered React application with:

- dashboard monitoring views
- camera management screens
- analytics and reporting pages
- settings and profile pages
- authentication flows for login, registration, and email verification

### Backend

The backend is a FastAPI application that exposes REST endpoints under `/api/v1` and a WebSocket endpoint at `/ws/dashboard`.

### Database

The backend uses SQLAlchemy with a PostgreSQL-oriented schema. The data model includes tables for users, roles, cameras, restricted zones, detections, AI events, reports, refresh tokens, and user settings.

### AI Engine

The AI engine is implemented in the backend under the AI package. It loads the YOLO model, tracks objects across frames, evaluates heuristics, and emits events that are saved to the database and broadcast to the UI.

### Notification Flow

The AI processor and services emit events that are sent to the WebSocket manager, which broadcasts them to connected clients.

### Camera Flow

A camera can be registered as:

- a live feed
- a USB/Webcam source
- an uploaded video asset

Once started, the backend streams the processed output to the frontend and stores alert metadata.

### Data Flow

1. Camera input is read and processed by the AI engine.
2. Detections are tracked and evaluated by business rules.
3. Events are persisted to the database.
4. Alerts are broadcast to the dashboard over WebSocket.
5. Reports and analytics are built from the stored detection history.

---

## Tech Stack

| Layer     | Technologies                                                                                               |
| --------- | ---------------------------------------------------------------------------------------------------------- |
| Frontend  | React, TypeScript, Vite, React Router, Axios, i18next, Tailwind CSS, Recharts, Framer Motion, Lucide React |
| Backend   | FastAPI, Uvicorn, SQLAlchemy, Pydantic, Python-JOSE, bcrypt                                                |
| AI        | Ultralytics, YOLOv8, OpenCV, NumPy, PyTorch                                                                |
| Database  | PostgreSQL-compatible SQLAlchemy models with UUID/JSONB support                                            |
| Auth      | JWT, refresh tokens, role-based access checks, email verification flow                                     |
| Reporting | FPDF, pandas, openpyxl, CSV export                                                                         |
| Realtime  | WebSocket support via FastAPI and a connection manager                                                     |

---

## Project Folder Structure

```text
.
├── backend/
│   ├── app/
│   │   ├── ai/
│   │   ├── api/
│   │   │   └── v1/
│   │   ├── core/
│   │   ├── database/
│   │   ├── models/
│   │   ├── repositories/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── utils/
│   │   └── websocket/
│   ├── tests/
│   ├── uploads/
│   ├── requirements.txt
│   └── .env
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── i18n/
│   │   ├── pages/
│   │   ├── services/
│   │   └── main.tsx
│   ├── package.json
│   └── vite.config.ts
├── docs/
└── README.md
```

### Key folders

- backend/app/api/v1: REST routers for authentication, cameras, users, reports, settings, AI events, and WebSocket.
- backend/app/ai: AI processing loop, tracker wrappers, and YOLO runtime integration.
- backend/app/services: business logic for AI events, reports, camera operations, and decision evaluation.
- backend/app/repositories: database access helpers for cameras, reports, users, settings, and detections.
- backend/app/models: SQLAlchemy model definitions.
- frontend/src/pages: dashboard, cameras, analytics, settings, login, and profile screens.
- frontend/src/services: API client, WebSocket client, and notification helpers.
- uploads: runtime storage for avatars, uploaded videos, AI screenshots, and generated assets.

---

## File Responsibilities

| File                                    | Responsibility                                                                                                 |
| --------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| backend/app/main.py                     | Creates the FastAPI app, wires middleware, mounts uploads, includes routers, and initializes app startup work. |
| backend/app/api/v1/auth.py              | Registration, login, refresh, email verification, and rate-limited authentication flows.                       |
| backend/app/api/v1/cameras.py           | Camera creation, zone management, start/stop analysis, stream access, and camera deletion.                     |
| backend/app/api/v1/reports.py           | Report summaries, generated reports, and CSV/Excel/PDF export endpoints.                                       |
| backend/app/api/v1/settings.py          | User settings retrieval, update, and reset, including AI config propagation.                                   |
| backend/app/api/v1/ai.py                | AI event listing, event retrieval, screenshot access, and manual event registration.                           |
| backend/app/api/v1/websocket_api.py     | WebSocket authentication and connection handling for live dashboard updates.                                   |
| backend/app/ai/processor.py             | Main AI processing loop, model loading, tracking, heuristics, state management, and event emission.            |
| backend/app/services/decision_engine.py | Threat severity classification used by the AI pipeline.                                                        |
| backend/app/services/ai_service.py      | Persists AI events, writes screenshots, and broadcasts events.                                                 |
| backend/app/services/report_service.py  | Aggregates report and analytics statistics from detections.                                                    |
| backend/app/models/models.py            | Core database schema and entity definitions.                                                                   |
| backend/app/database/session.py         | SQLAlchemy engine/session configuration and schema compatibility support.                                      |
| frontend/src/App.tsx                    | Main application shell, routing, authentication state, notifications, and WebSocket lifecycle.                 |
| frontend/src/pages/Dashboard.tsx        | Live monitoring dashboard, camera selection, alarms, and stream visualization.                                 |
| frontend/src/pages/Cameras.tsx          | Camera administration and provisioning interface.                                                              |
| frontend/src/pages/Analytics.tsx        | Analytics and reporting dashboard UI.                                                                          |
| frontend/src/pages/Settings.tsx         | Runtime settings and AI configuration UI.                                                                      |
| frontend/src/services/api.ts            | Shared Axios client and API service wrappers.                                                                  |
| frontend/src/services/socket.ts         | WebSocket client contract and message handling.                                                                |

---

## Installation

### Prerequisites

- Python 3.12 or newer
- Node.js 18 or newer
- npm
- PostgreSQL database instance for the backend

### 1. Clone the repository

```bash
git clone https://github.com/eslam-adel25/AeroGuard-AI.git
cd AeroGuard-AI
```

### 2. Backend setup

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Frontend setup

```bash
cd ../frontend
npm install
```

### 4. Configure environment variables

Create a local `.env` file in the backend folder with the required values. At minimum, define the database connection string and auth secret.

Example:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/aeroguard_db
SECRET_KEY=change-me
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

Additional optional settings are documented below.

### 5. Create the database schema

The application creates tables at startup by calling the SQLAlchemy metadata creation routine in the app startup path. Ensure your PostgreSQL database is available and reachable before launching the backend.

---

## Running the Project

### Backend

From the backend folder:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API documentation will be available at:

- http://127.0.0.1:8000/docs
- http://127.0.0.1:8000/redoc

### Frontend

From the frontend folder:

```bash
npm run dev
```

The frontend is typically served at:

- http://localhost:5173

### Production build

```bash
cd frontend
npm run build
```

### Preview build output

```bash
npm run preview
```

---

## Available Scripts

### Frontend scripts

| Script          | Purpose                                           |
| --------------- | ------------------------------------------------- |
| npm run dev     | Start the Vite development server.                |
| npm run build   | Type-check and build the frontend bundle.         |
| npm run lint    | Run the ESLint checks configured for the project. |
| npm run preview | Preview the built frontend locally.               |

### Backend execution

The backend is run directly with Uvicorn rather than through a package script in the repository.

---

## Environment Variables

The backend and frontend read the following environment variables from the environment or a local `.env` file.

| Variable                          | Used by  | Purpose                                                                                                          |
| --------------------------------- | -------- | ---------------------------------------------------------------------------------------------------------------- |
| DATABASE_URL                      | backend  | SQLAlchemy connection string for PostgreSQL. Required.                                                           |
| SECRET_KEY or JWT_SECRET          | backend  | JWT signing secret. If unset, the code falls back to a hard-coded default, which is not suitable for production. |
| ALGORITHM                         | backend  | JWT algorithm. Defaults to HS256.                                                                                |
| ACCESS_TOKEN_EXPIRE_MINUTES       | backend  | Access token lifetime in minutes. Defaults to 60.                                                                |
| SMTP_HOST                         | backend  | SMTP server host for verification emails.                                                                        |
| SMTP_PORT                         | backend  | SMTP server port. Defaults to 587 if provided.                                                                   |
| SMTP_USERNAME or SMTP_USER        | backend  | SMTP username.                                                                                                   |
| SMTP_PASSWORD or SMTP_PASS        | backend  | SMTP password.                                                                                                   |
| MAIL_FROM or EMAIL_FROM           | backend  | Sender email address.                                                                                            |
| MAIL_FROM_NAME                    | backend  | Sender display name. Defaults to AeroGuard AI.                                                                   |
| FRONTEND_BASE                     | backend  | Base URL used in email verification links. Defaults to http://localhost:5173.                                    |
| EMAIL_VERIFICATION_EXPIRE_MINUTES | backend  | Email verification token lifetime in minutes. Defaults to 15.                                                    |
| REQUIRE_EMAIL_VERIFICATION        | backend  | Enables or disables the email verification gate for registration/login.                                          |
| HOST                              | backend  | Host value used by the startup entry point.                                                                      |
| PORT                              | backend  | Port value used by the startup entry point. Defaults to 8000.                                                    |
| VITE_API_BASE_URL                 | frontend | Overrides the API base URL used by the Axios client. Defaults to /api/v1.                                        |
| VITE_WS_BASE_URL                  | frontend | Overrides the WebSocket base URL. Defaults to the current host.                                                  |

> Do not commit secrets to source control. Keep production secrets in a secure secret store or environment-managed configuration.

---

## API Overview

The backend exposes its REST API under `/api/v1`.

| API group       | Routes                                                                                          | Notes                                                                      |
| --------------- | ----------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| Authentication  | `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/verify`                                | Registration, login, token refresh, and verification.                      |
| Users & Profile | `/users/profile`, `/users/profile/password`, `/users/profile/avatar`, `/users/roles`, `/users/` | Profile data, password changes, avatar upload, and admin user management.  |
| Cameras         | `/cameras/`, `/cameras/{id}/start`, `/cameras/{id}/stop`, `/cameras/{id}/zones`                 | Camera registration, analytics start/stop, and restricted-zone management. |
| AI Events       | `/ai/events`, `/ai/events/{event_id}`, `/ai/events/{event_id}/screenshot`                       | AI event history and screenshot retrieval.                                 |
| Reports         | `/reports/`, `/reports/dashboard`, `/reports/generate`, `/reports/export/*`                     | Dashboard summaries, report generation, and file exports.                  |
| Settings        | `/settings/`, `/settings/reset`                                                                 | User-specific runtime configuration and AI settings.                       |
| WebSocket       | `/ws/dashboard`                                                                                 | Broadcasts live alerts and monitoring events to connected clients.         |

---

## Database

The persistence layer is implemented with SQLAlchemy and is centered around the models defined in the backend.

### Main entities

- Role: user role definitions such as Administrator and Officer.
- User: account profile, credentials, verification state, and role association.
- Camera: camera metadata, source type, status, and owner.
- RestrictedZone: polygon-based restricted-area annotations per camera.
- Detection: persisted detection records with confidence, priority, and violation metadata.
- AIEvent: persisted AI-generated event records and screenshots.
- Tracking: tracking metadata for objects over time.
- Report: generated report metadata, filters, summary/charts/details payloads, and export history.
- UserSettings: per-user configuration for AI, UI, notifications, and security.
- RefreshToken / EmailVerificationToken / ActivityLog: auth and lifecycle management.

### Notes

- The schema uses PostgreSQL-friendly UUID fields and JSON/JSONB-style structures.
- The backend includes compatibility logic that inspects existing columns and adds missing ones during startup.

---

## AI Pipeline

The AI pipeline is implemented in the backend AI module and is responsible for transforming camera frames into detections and alerts.

### Processing stages

1. Frame ingestion: OpenCV reads frames from a camera source or uploaded video.
2. Model inference: YOLOv8 performs object detection.
3. Tracking: object tracks are maintained across frames.
4. Rule evaluation: heuristics detect restricted zones, wrong direction, loitering, abandoned-bag ownership, and fire/smoke-related scenarios.
5. Event emission: the backend persists detections and AI events, saves screenshots, and broadcasts updates to the UI.

### Current detection logic

The implemented pipeline includes support for:

- person detection
- bag/suitcase/backpack detection
- vehicle detection
- smoke/fire detection
- alert severity classification

The code also includes visualization overlays such as display IDs and ownership annotations for detected bags.

---

## Localization

The frontend uses i18next with two active language bundles:

- English
- Arabic

The language selection is stored client-side under the `ag_language` key, and the dashboard, auth flows, settings, and analytics UI pull their labels from the translation files in the frontend i18n directory.

---

## Security

Security is implemented across authentication, authorization, and transport layers.

### Authentication

- user registration and login endpoints
- JWT access tokens
- refresh-token persistence and revocation
- optional email verification requirement

### Authorization

- role-based access checks for administrators and regular users
- camera ownership checks for user-scoped access
- protected routes for profile, camera, settings, and report operations

### Password handling

Passwords are hashed with bcrypt before persistence.

### Transport protection

The backend adds security headers and an explicit CORS allowlist for development origins. The app also mounts uploaded media under a dedicated static route.

---

## Notifications

Notifications are surfaced in two ways:

- the live WebSocket stream for dashboard updates
- the in-app notification collection used by the React UI

The backend broadcasts messages such as:

- `ai_event`
- `new_alert`
- `alarm_state`
- `camera_status`
- `ai_status`

These messages are consumed by the frontend notification service and dashboard views.

---

## Reports

Reports are generated from stored detections and exported in several formats.

### Supported export formats

- CSV
- Excel (.xlsx)
- PDF

The report system collects filters, summary metrics, charts, details, and export history for each generated report.

---

## Analytics

The analytics layer is exposed through the reports dashboard endpoint and powers the UI analytics screen.

It provides:

- totals and violation counts
- severity breakdowns
- detection type summaries
- recent alerts
- top cameras
- timeline views for the selected date range

---

## Deployment

The repository does not currently include a Dockerfile or container configuration.

For deployment, the application should be run as:

- one backend process serving the FastAPI app
- one frontend build served through a static host or reverse proxy
- a reachable PostgreSQL instance for the backend database

Recommended deployment considerations:

- set production secrets for JWT and email SMTP
- ensure uploaded media directories are writable
- review the pinned Python dependencies before shipping to production
- place the frontend behind a reverse proxy if serving from the same host as the API

---

## Troubleshooting

### The backend fails to start because DATABASE_URL is missing

Set the environment variable in your shell or local `.env` file before running the backend.

### The AI engine does not initialize

Check that the model file exists at the path expected by the backend and that dependencies such as OpenCV and Ultralytics are installed correctly.

### WebSocket connections fail

Confirm that the client has a valid JWT token and that the backend is reachable at the expected host/port.

### Email verification is not working

Provide SMTP settings and ensure the email verification feature is enabled with the appropriate environment variables.

---

## FAQ

### What is AeroGuard AI?

AeroGuard AI is a surveillance operations platform that combines computer vision, live camera management, alerting, analytics, and reporting into one system.

### Does the project support live streaming?

Yes. The backend supports live streams, USB/Webcam sources, and uploaded videos.

### Can I run the frontend and backend locally?

Yes. The project includes a FastAPI backend and a Vite-based React frontend that can run together in development mode.

### Is Docker supported?

Not in the repository as currently checked in. The project is currently configured for direct Python and Node.js deployment.

---

## Contributing

Contributions are welcome.

1. Fork the repository.
2. Create a feature branch.
3. Make focused changes with clear intent.
4. Update relevant documentation if behavior changes.
5. Submit a pull request with context and testing notes.

The backend test suite lives under the backend/tests folder and covers areas such as authentication flow, AI event handling, and report logic.

---

## License

No license file is currently present in the repository, so the project license is not specified.

---

## Author

### Eslam Adel

- GitHub: [eslam-adel25](https://github.com/eslam-adel25)
- Repository: [AeroGuard-AI](https://github.com/eslam-adel25/AeroGuard-AI)

---

## Acknowledgements

This project builds on a strong open-source ecosystem, including:

- FastAPI
- React and Vite
- SQLAlchemy
- Ultralytics / YOLOv8
- OpenCV
- Tailwind CSS
- Recharts
- i18next
- FPDF and openpyxl

---

For deeper implementation detail, see the documentation under [docs](docs/).
