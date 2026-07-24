# Installation, Build, and Run

This document reflects the local development workflow for the current repository layout.

Prerequisites

- Python 3.10+ or 3.12+ for the backend environment.
- Node.js 18+ and npm for the frontend.
- A database reachable through DATABASE_URL.

Backend setup

1. Create and activate a virtual environment.

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
```

2. Install backend dependencies.

```bash
pip install -r requirements.txt
```

3. Set the required environment variables.

```bash
set DATABASE_URL=postgresql+psycopg2://user:pass@localhost:5432/aeroguard
set SECRET_KEY=change-me
```

4. Start the API.

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The Swagger UI will be available at http://127.0.0.1:8000/docs.

Frontend setup

1. Install frontend dependencies.

```bash
cd ../frontend
npm install
```

2. Start the Vite dev server.

```bash
npm run dev
```

3. Build for production.

```bash
npm run build
```

Notes

- The frontend defaults to the same-origin /api/v1 base URL when VITE_API_BASE_URL is not provided.
- The Vite config proxies /api, /ws, and /uploads to the backend during development.
- The current repository includes a backend test suite under backend/tests; you can run individual tests with pytest.
