# Authentication Flow

This document describes the authentication and session flow implemented in backend/app/api/v1/auth.py and related modules.

1. Registration
   - POST /api/v1/auth/register accepts full_name, username, email, password, phone, and organization.
   - The endpoint creates a default Officer role when needed and hashes the password with bcrypt.
   - A verification token is created and a verification email is attempted if SMTP settings are configured.
   - The API can require email verification through the REQUIRE_EMAIL_VERIFICATION environment flag.

2. Login
   - POST /api/v1/auth/login validates the submitted username/password pair.
   - If email verification is required, the account must already be verified before the login proceeds.
   - On success it issues a JWT access token and stores a server-side refresh token with expiry metadata.
   - Login activity is recorded in the activity_logs table.

3. Token refresh
   - POST /api/v1/auth/refresh accepts a refresh token and issues a new access token when the token is valid and not revoked.

4. Email verification
   - GET /api/v1/auth/verify?token=... validates the token and marks the account as verified.
   - The same flow can apply pending username or email changes.
   - A separate OTP verification route is also available for code-based verification.

5. Logout and session revocation
   - POST /api/v1/auth/logout revokes the supplied refresh token.
   - The user profile endpoints also support revoking all sessions for the current user.

Security notes

- Access tokens are JWTs signed with the configured secret from SECRET_KEY or JWT_SECRET.
- The backend uses backend/app/core/auth_middleware.py to protect routes and enforce role-based access.
- Authentication endpoints are rate-limited in memory, which is suitable for development and small deployments but not a substitute for Redis-backed or gateway-level rate limiting in production.
