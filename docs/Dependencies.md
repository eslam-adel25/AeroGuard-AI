# Dependencies

This document lists observed dependencies in the repository.

Frontend

- See `frontend/package.json` for exact dependencies and devDependencies. Key runtime deps:
  - `react`, `react-dom` (React 19)
  - `axios` (HTTP client)
  - `recharts` (charts)
  - `react-i18next` / `i18next` (i18n)
  - `lucide-react` (icons)

Backend (inferred)

The project does not include a `requirements.txt`. These packages are referenced in the code and are required to run the backend (install and pin versions before deployment):

- `fastapi`
- `uvicorn`
- `sqlalchemy`
- `psycopg2-binary` (Postgres driver)
- `python-dotenv` (optional, for .env files)
- `python-jose[cryptography]` (JWT)
- `bcrypt` (password hashing)
- `python-multipart` (file uploads)
- `pillow` (image resizing)
- `fpdf` (PDF generation)
- `pandas` (Excel/report generation)
- `ultralytics` (YOLOv8 model API)
- `opencv-python`
- `numpy`

Optional / integration

- `openpyxl` — required if Excel export is used (`reports/export/excel`).

Recommendation

- Create and commit a pinned `requirements.txt` or `pyproject.toml` before production.
- Use a virtual environment and pin versions via `pip freeze > requirements.txt` after installation and verification.
