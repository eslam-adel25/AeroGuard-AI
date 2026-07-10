# Authentication Flow (implementation-derived)

This document describes the authentication and session flows implemented in `awro-guard/backend/app/api/v1/auth.py` and related modules.

1. Registration (`POST /api/v1/auth/register`)
   - Accepts `full_name`, `username`, `email`, `password`, `phone`, `organization` via `UserRegister` schema.
   - Creates a `User` with role `Officer` (creates role if missing).
   - Password is hashed with `bcrypt` via `core/security.hash_password`.
   - Creates an `EmailVerificationToken` record and attempts to send a verification email (best-effort). A user remains `is_verified=False` until verification.
   - Simple in-memory rate-limiting protects the endpoint.

2. Login (`POST /api/v1/auth/login`)
   - Accepts `username` and `password` via `UserLogin`.
   - Verifies password using `verify_password`.
   - Requires `is_verified=True` (email verified) to proceed.
   - On success creates an access token (JWT) and a server-side refresh token (`RefreshToken` record).
   - Refresh tokens are long-lived (7 days in code) and can be revoked.
   - Activity logged in `activity_logs`.

3. Token Refresh (`POST /api/v1/auth/refresh`)
   - Exchange a valid refresh token for a new access token. Server validates refresh token exists and not revoked.

4. Email Verification (`GET /api/v1/auth/verify?token=...`)
   - Validates `EmailVerificationToken` and applies pending `new_email` or `new_username` changes if present, or simply marks `is_verified=True`.

5. Resend Verification (`POST /api/v1/auth/resend-verification`)
   - Reissues verification tokens with a resend limit protected in code.

6. Logout (`POST /api/v1/auth/logout`)
   - Revokes the supplied refresh token in the DB.

Security notes

- Access tokens are JWTs signed with `SECRET_KEY` / `JWT_SECRET` and validated using `core/security.verify_token`.
- `core/auth_middleware.get_current_user` and `role_required` are used to protect endpoints and enforce RBAC.
- The project includes lightweight in-memory rate-limiting for authentication endpoints; this is NOT a replacement for a distributed rate-limiter in production.

Refresh token storage

- Refresh tokens are persisted in the `refresh_tokens` table with `expires_at` and `revoked` flags, enabling server-side revocation.
