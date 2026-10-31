# Security and Hardening Summary

This summary captures the security controls that are implemented in the current codebase.

Authentication and authorization

- JWT-based authentication is implemented in backend/app/core/security.py.
- Role-based access checks are enforced through backend/app/core/auth_middleware.py.
- Passwords are hashed with bcrypt before storage.
- Active customer feature permissions are resolved from CustomerProfile and
  CustomerFeaturePermission on each protected API request. The Owner feature
  registry controls the supported keys: dashboard, cameras, analytics, alerts,
  profile, and settings. Admin and Officer requests resolve membership from
  database relationships and are scoped to one CustomerProfile. The Owner role
  is resolved from the database and has platform-wide resource access; Admin
  does not receive global privileges. Customer-resource access requires an
  Active user account and an active `PLATFORM_CUSTOMER` profile; Pending or
  inactive user/profile status is denied.
- Analytics and Alerts permissions each allow read-only AI-event investigation;
  acknowledging events and creating manual events still require Alerts.
- AI-event screenshot files require an active customer with either Analytics
  or Alerts, and retain the existing event-camera ownership check.
- Camera creation preflights max_camera_count in the API and enforces it again
  under a customer-profile row lock in the repository, covering alternate
  creation paths and concurrent requests. It counts all owned cameras
  regardless of status; a NULL quota remains unlimited. Owner-created cameras
  require an explicit existing CustomerProfile and are checked against that
  customer's quota.

Rate limiting

- Authentication endpoints use an in-memory throttling mechanism to reduce brute-force attempts.
- This is appropriate for development and small deployments, but production deployments should consider a shared rate-limiter.

Uploads and file handling

- Camera uploads and profile avatars are validated for extension and size.
- Uploaded assets are stored under backend/uploads and are removed when the owning camera is deleted.
- Customer avatars, camera videos, and AI-event screenshots are served only
  after active-account, feature, and tenant ownership checks. Owner may access
  these files platform-wide. Reports remain available through report ownership
  checks, and customer exports are restricted to the report tenant.

WebSocket security

- The WebSocket route validates the access token from the query string before accepting a connection.
- Customer sockets receive only messages for their resolved CustomerProfile
  and enabled feature. Owner sockets are authenticated against the database
  Owner role and receive platform-wide messages.
- Current account and feature authorization is rechecked before customer
  message delivery. WebSocket connections are removed when authorization fails.
- Owner self-service profile, avatar, password, session, and email operations
  remain limited to the authenticated Owner's own account; session responses
  omit refresh-token values.

Tenant data and migration status

- CustomerProfile is the canonical tenant identity. Existing data with a
  verified owner relationship remains usable; ambiguous legacy Officer
  membership and unowned report data are denied to customers and preserved.
- Migration 006 is an additive nullable ownership schema. It has been applied
  only to staging; production has not been migrated or backfilled. Ambiguous
  legacy Officer membership and reports remain unresolved and inaccessible to
  customer tenants.

CORS and headers

- The app adds security headers and a constrained CORS allowlist in backend/app/main.py.

Secrets and email delivery

- SMTP and JWT settings are read from environment variables.
- The backend can log verification email content when SMTP is not configured, but this is not a production email delivery path.

Recommended hardening for production

- Use a managed secret store for DATABASE_URL, JWT secrets, and SMTP credentials.
- Put the app behind HTTPS and consider a reverse proxy or API gateway.
- Replace the in-memory rate limiter with a distributed solution if the deployment scales beyond a single instance.
