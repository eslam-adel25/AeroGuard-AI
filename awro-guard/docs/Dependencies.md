# Dependencies

This document lists observed dependencies in the repository.

Frontend

- See `awro-guard/frontend/package.json` for exact dependencies and devDependencies. Key runtime deps:
  - `react`, `react-dom` (React 19)
  - `axios` (HTTP client)
  - `recharts` (charts)
  - `react-i18next` / `i18next` (i18n)
  - `lucide-react` (icons)

Backend (inferred)

The backend includes a pinned requirements file at `awro-guard/backend/requirements.txt`. These packages are referenced in the code and are required to run the backend (install and pin versions before deployment):

- `fastapi`
- `uvicorn`
- `sqlalchemy`
- `psycopg2-binary` (Postgres driver)
- `python-dotenv` (optional, for .env files)
- `python-jose[cryptography]` (JWT)
- `bcrypt` (password hashing)
- `python-multipart` (file uploads)
- `Pillow` (image resizing)
- `fpdf2` (PDF generation)
- `pandas` (Excel/report generation)
- `openpyxl` (Excel export)
- `email-validator` (Pydantic EmailStr validation)
- `websockets` (WebSocket support)
- `starlette` (ASGI/web utilities)
- `ultralytics` (YOLOv8 model API)
- `opencv-python`
- `numpy`

Optional / integration

- `openpyxl` — required if Excel export is used (`reports/export/excel`).

Recommendation

- The backend already includes a pinned requirements file at `awro-guard/backend/requirements.txt`; verify these versions in your target Python 3.12 environment before production.
- Use a virtual environment and keep dependency pins under source control for reproducibility.
