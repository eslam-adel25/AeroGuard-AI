# Environment Variables

The backend reads several environment variables from the runtime environment or a local .env file. Do not commit secrets to source control.

| Variable                                                   | Purpose                                            | Notes                                                                                            |
| ---------------------------------------------------------- | -------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| DATABASE_URL                                               | SQLAlchemy database connection string              | Required. Must point to the intended environment's PostgreSQL database.                         |
| ENVIRONMENT                                                | Runtime environment name                           | Set to `production` to enforce production secret validation.                                   |
| SECRET_KEY or JWT_SECRET                                   | JWT signing secret                                 | Required in production; use a random value of at least 32 bytes.                                |
| ALGORITHM                                                  | JWT signing algorithm                              | Defaults to HS256.                                                                              |
| ACCESS_TOKEN_EXPIRE_MINUTES                                | Access token lifetime in minutes                   | Defaults to 60.                                                                                 |
| REQUIRE_EMAIL_VERIFICATION                                 | Enables the email-verification gate for login      | Supported values include 1/true/yes/on.                                                         |
| EMAIL_VERIFICATION_EXPIRE_MINUTES                          | Lifetime of email-verification tokens              | Defaults to 15 minutes.                                                                         |
| SMTP_HOST / SMTP_PORT / SMTP_USER / SMTP_PASS / EMAIL_FROM | SMTP configuration for verification email delivery | Configure when verification is enabled; missing SMTP may log verification content.              |
| FRONTEND_BASE                                              | Frontend URL used in verification links            | Set to the deployed HTTPS frontend URL.                                                          |
| HOST / PORT                                                | Host and port for the backend entrypoint           | Used when running backend/app/main.py directly.                                                  |
| VITE_API_BASE_URL                                          | Frontend API base URL                              | Build-time setting; defaults to `/api/v1` for same-origin hosting.                               |
| VITE_WS_BASE_URL                                           | Frontend WebSocket base URL                        | Build-time setting; defaults to the current origin; use `wss://` in production if separate.      |

Security reminder

- Keep secrets in environment variables, CI/CD secret stores, or a managed secret provider rather than committing them to the repository.
- CORS origins are currently hard-coded in `backend/app/main.py`, not controlled by an environment variable. Update the allowlist for a separate frontend origin, or serve API and WebSocket traffic through a same-origin HTTPS reverse proxy.
- Do not use the development fallback signing secret in production.
