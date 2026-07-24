# Dependencies

This document reflects the package lists currently present in the repository.

Frontend

- See frontend/package.json for the installed frontend dependencies.
- Key runtime libraries include React 19, React Router, Axios, Recharts, Framer Motion, i18next, and Lucide React.
- Development tooling includes Vite, TypeScript, ESLint, Tailwind CSS, PostCSS, and Autoprefixer.

Backend

- The pinned Python dependency list lives in backend/requirements.txt.
- The main backend stack includes FastAPI, Uvicorn, SQLAlchemy, psycopg2-binary, python-jose, bcrypt, python-dotenv, python-multipart, Pillow, fpdf2, pandas, openpyxl, email-validator, websockets, ultralytics, opencv-python, and numpy.

Notes

- The backend requirements file is the authoritative dependency source for server-side installs.
- The Excel export route will fail with HTTP 501 if openpyxl is missing from the server environment.
- Dependency pins should be validated in the target Python environment before deployment.
