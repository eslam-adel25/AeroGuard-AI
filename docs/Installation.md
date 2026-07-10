# Installation, Build & Run (derived from code)

This document describes how to run the project locally for development and how to provision required environment variables observed in the code.

Prerequisites

- Python 3.10+ (the code appears to run on modern CPython; tests ran with Python 3.12 in the environment used for inspection).
- Node.js 18+ and npm for the frontend.
- PostgreSQL database for production (local SQLite is not configured; SQLAlchemy engine expects `DATABASE_URL`).

Backend – Python environment

1. Create and activate virtualenv

```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate
```

2. Install dependencies

There is no `requirements.txt` in the repository. Based on imports, a minimal `pip` install list includes:

```text
fastapi
uvicorn
sqlalchemy
psycopg2-binary
python-dotenv
python-jose[cryptography]
bcrypt
python-multipart
pillow
fpdf
pandas
ultralytics
opencv-python
numpy
```

Create `requirements.txt` by pinning versions appropriate for your environment before deploying.

3. Environment variables (observed in code)

| Variable                    |                                     Description | Example                                                  | Required |
| --------------------------- | ----------------------------------------------: | -------------------------------------------------------- | -------: |
| DATABASE_URL                |            SQLAlchemy database URL (PostgreSQL) | postgresql+psycopg2://user:pass@localhost:5432/aeroguard |      Yes |
| SECRET_KEY / JWT_SECRET     |                              JWT signing secret | (keep secret)                                            |      Yes |
| ACCESS_TOKEN_EXPIRE_MINUTES | Access token expiry in minutes (defaults to 60) | 60                                                       |       No |
| ALGORITHM                   |               JWT algorithm (defaults to HS256) | HS256                                                    |       No |
| SMTP_HOST                   |      SMTP server host (for verification emails) | smtp.example.com                                         |       No |
| SMTP_PORT                   |                          SMTP server port (587) | 587                                                      |       No |
| SMTP_USER                   |                                   SMTP username | user@example.com                                         |       No |
| SMTP_PASS                   |                                   SMTP password | (secret)                                                 |       No |
| EMAIL_FROM                  |                         From address for emails | no-reply@aeroguard.local                                 |       No |
| FRONTEND_BASE               |        Frontend base URL for verification links | http://localhost:5173                                    |       No |

4. Run backend (development)

```bash
cd backend
.venv\Scripts\activate
pip install -r requirements.txt  # create this file first
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Visit documentation at `http://127.0.0.1:8000/docs` once the server is running.

Frontend – Node.js

1. Install dependencies

```bash
cd frontend
npm install
```

2. Development

```bash
npm run dev
```

3. Production build

```bash
npm run build
# serve dist/ with any static server
```

Notes and verification

- Frontend `api.ts` client points to `http://127.0.0.1:8000/api/v1` by default.
- WebSocket connects to `ws://127.0.0.1:8000/ws/dashboard?token=<token>` in the frontend socket helper.
- The repository includes Vite + TypeScript configuration in `frontend/` (`tsconfig.app.json`, `vite.config.ts`).

Testing

- Backend unit tests (small set observed):

```bash
# from backend/ with virtualenv active
python -m pytest -q tests/test_security_helpers.py
```

This repo's tests exercise security helper functions.

If you want, I can produce a pinned `requirements.txt` and a `package.json` upgrade plan for production-ready bundles.
