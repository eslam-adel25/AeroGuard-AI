# AeroGuard AI

Comprehensive, implementation-backed documentation for the AeroGuard AI repository. This documentation is derived directly from the repository sources (backend and frontend) and does not invent behavior beyond the code.

This repository contains:

- A FastAPI backend implementing REST endpoints, AI pipeline, WebSocket push notifications, persistence and reporting.
- A React + TypeScript frontend built with Vite providing the dashboard and administrative UI.

This README is an index; detailed reference documents are available in the `docs/` directory.

Docs

- [System Architecture & Overview](docs/Architecture.md)
- [REST API Reference](docs/API.md)
- [AI Engine & Modules](docs/AI.md)
- [Database Schema & Models](docs/Database.md)
- [Security & Hardening Summary](docs/Security.md)
- [Installation & Build](docs/Installation.md)
- [Folder Structure](docs/FolderStructure.md)
- [Environment Variables](docs/EnvVars.md)
- [Dependencies](docs/Dependencies.md)
- [Authentication Flow](docs/Auth.md)
- [WebSockets](docs/WebSockets.md)
- [Camera Pipeline](docs/CameraPipeline.md)
- [Reports System](docs/Reports.md)
- [Settings System](docs/Settings.md)
- [Reference Map](docs/Reference.md)

Quickstart (development)

1. Backend

```bash
cd awro-guard/backend
python -m venv .venv
# Windows
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

2. Frontend

```bash
cd awro-guard/frontend
npm install
npm run dev
```

Where to look next

- Environment variables the backend reads: see [docs/EnvVars.md](docs/EnvVars.md).
- The backend exposes an OpenAPI UI at `/docs` when running locally.
- The frontend's API client and expected endpoints are in `awro-guard/frontend/src/services/api.ts`.

Important implementation notes

- A pinned backend requirements file exists at `awro-guard/backend/requirements.txt`. Python dependencies should still be reviewed before production deployment (see `docs/Dependencies.md`).
- No Dockerfile or container definitions are present in the repository. Containerized deployment is recommended for production.
- The backend already includes a pinned dependency manifest at `awro-guard/backend/requirements.txt`.
- The backend expects a `DATABASE_URL` environment variable and uses PostgreSQL-specific types (`UUID`, `JSONB`).

For implementation-level details, open any of the `docs/*.md` files.
