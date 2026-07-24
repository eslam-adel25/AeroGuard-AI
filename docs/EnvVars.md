# Environment Variables

The backend reads several environment variables from the runtime environment or a local .env file. Do not commit secrets to source control.

| Variable                                                   | Purpose                                            | Notes                                                                                            |
| ---------------------------------------------------------- | -------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| DATABASE_URL                                               | SQLAlchemy database connection string              | Required. The application raises a runtime error if it is absent.                                |
| SECRET_KEY or JWT_SECRET                                   | JWT signing secret                                 | Required for production-like deployments; otherwise the code falls back to a hard-coded default. |
| ALGORITHM                                                  | JWT signing algorithm                              | Defaults to HS256.                                                                               |
| ACCESS_TOKEN_EXPIRE_MINUTES                                | Access token lifetime in minutes                   | Defaults to 60.                                                                                  |
| REQUIRE_EMAIL_VERIFICATION                                 | Enables the email-verification gate for login      | Supported values include 1/true/yes/on.                                                          |
| EMAIL_VERIFICATION_EXPIRE_MINUTES                          | Lifetime of email-verification tokens              | Defaults to 15 minutes.                                                                          |
| SMTP_HOST / SMTP_PORT / SMTP_USER / SMTP_PASS / EMAIL_FROM | SMTP configuration for verification email delivery | Optional; if missing, the backend logs the message content instead of sending it.                |
| FRONTEND_BASE                                              | Frontend URL used in verification links            | Defaults to http://localhost:5173.                                                               |
| HOST / PORT                                                | Host and port for the backend entrypoint           | Used when running backend/app/main.py directly.                                                  |

Security reminder

- Keep secrets in environment variables, CI/CD secret stores, or a managed secret provider rather than committing them to the repository.
