# Security & Hardening Summary (implementation-derived)

This summary enumerates security measures implemented in the codebase and references the files where each protection appears.

Authentication & Authorization

- JWT-based authentication
  - Token creation and validation performed in `backend/app/core/security.py` (uses `python-jose`).
  - `ACCESS_TOKEN_EXPIRE_MINUTES` controls expiration (defaults to 60 mins if unset).
- Password hashing with bcrypt in `backend/app/core/security.py`.
- Role-based access control via `backend/app/core/auth_middleware.py` and `role_required()` decorator.

Rate limiting and brute-force protection

- A lightweight in-memory throttling mechanism protects login and registration routes in `backend/app/api/v1/auth.py` (per-client and per-username buckets).
- This is suitable for small deployments; for production a distributed rate limiter (Redis or API gateway rate limits) is recommended.

Input, uploads and file handling

- Avatar and video uploads are validated for extension and size in `backend/app/api/v1/users.py` and `backend/app/api/v1/cameras.py`.
- Uploaded files are saved under the `uploads/` directory and are removed when camera entries are deleted (camera type UPLOAD).
- Screenshot writing for AI events is handled carefully and paths are stored on the model (`screenshot_path`).

Database safety

- SQLAlchemy query composition is used across repositories (parameterized queries). Use of `JSONB` accessors appears in `report_repository` but queries remain parameterized.

WebSocket security

- WebSocket endpoint `backend/app/api/v1/websocket_api.py` accepts `token` as a query parameter and validates via JWT helper.
- The WebSocket manager broadcasts JSON messages only; connection cleanup handles dead sockets.

CORS & headers

- Security headers are set by a custom middleware in `backend/app/main.py` (Content-Security-Policy, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy).
- CORS is configured with an explicit allowlist (localhost dev origins).

Email and secrets

- Email sending is implemented in `backend/app/core/emailer.py` using SMTP settings read from environment variables (SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, EMAIL_FROM).
- Secrets (JWT secret, SMTP credentials, DATABASE_URL) must be provided via environment variables. The repository uses `python-dotenv` if `.env` is present, but no `.env` is included in source control.

Session & refresh tokens

- Refresh tokens are stored server-side in `refresh_tokens` table and can be revoked.
- Password changes revoke refresh tokens for the user.

Audit & activity logs

- Activity events are recorded using `ActivityRepository` into `activity_logs` table.

What is missing or recommended

- No web application firewall or distributed rate limiter configured — recommend integration with Redis or API gateway for production.
- No HTTPS / TLS termination instructions (assume reverse proxy with TLS in front of Uvicorn).
- No secrets management shown (use environment variables and secret stores in production).
- No explicit CSRF tokens required because API uses Bearer tokens, but if cookies are used later, CSRF protection must be added.

If you want, I can expand this into a checklist of production hardening steps with suggested tool choices (Redis, Traefik, Nginx, Vault, etc.).
