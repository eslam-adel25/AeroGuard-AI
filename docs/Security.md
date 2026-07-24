# Security and Hardening Summary

This summary captures the security controls that are implemented in the current codebase.

Authentication and authorization

- JWT-based authentication is implemented in backend/app/core/security.py.
- Role-based access checks are enforced through backend/app/core/auth_middleware.py.
- Passwords are hashed with bcrypt before storage.

Rate limiting

- Authentication endpoints use an in-memory throttling mechanism to reduce brute-force attempts.
- This is appropriate for development and small deployments, but production deployments should consider a shared rate-limiter.

Uploads and file handling

- Camera uploads and profile avatars are validated for extension and size.
- Uploaded assets are stored under backend/uploads and are removed when the owning camera is deleted.

WebSocket security

- The WebSocket route validates the access token from the query string before accepting a connection.
- The connection manager cleans up dead sockets and only broadcasts JSON payloads.

CORS and headers

- The app adds security headers and a constrained CORS allowlist in backend/app/main.py.

Secrets and email delivery

- SMTP and JWT settings are read from environment variables.
- The backend can log verification email content when SMTP is not configured, but this is not a production email delivery path.

Recommended hardening for production

- Use a managed secret store for DATABASE_URL, JWT secrets, and SMTP credentials.
- Put the app behind HTTPS and consider a reverse proxy or API gateway.
- Replace the in-memory rate limiter with a distributed solution if the deployment scales beyond a single instance.
