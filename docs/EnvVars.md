# Environment Variables (observed in source)

The backend reads a small set of environment variables. Provide these in the environment (or in a local `.env` for development). Do NOT commit secrets to source control.

| Variable                      | Purpose                                       | Notes                                                                               |
| ----------------------------- | --------------------------------------------- | ----------------------------------------------------------------------------------- |
| `DATABASE_URL`                | SQLAlchemy DB connection string (Postgres)    | Required. Example: `postgresql+psycopg2://user:pass@host:5432/dbname`               |
| `SECRET_KEY` or `JWT_SECRET`  | JWT signing secret used by `security.py`      | Required. Keep secret. If both unset a `super_secret` default is used (not secure). |
| `ALGORITHM`                   | JWT signing algorithm (default `HS256`)       | Optional.                                                                           |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token expiry in minutes (default `60`) | Optional.                                                                           |
| `SMTP_HOST`                   | SMTP server host for verification emails      | Optional; needed for email verification flows.                                      |
| `SMTP_PORT`                   | SMTP port (e.g. `587`)                        | Optional.                                                                           |
| `SMTP_USER`                   | SMTP username                                 | Optional.                                                                           |
| `SMTP_PASS`                   | SMTP password                                 | Optional.                                                                           |
| `EMAIL_FROM`                  | From address used in outgoing emails          | Defaults to `no-reply@aeroguard.local` if unset.                                    |
| `FRONTEND_BASE`               | Frontend base URL used in verification links  | Default `http://localhost:5173`.                                                    |

Security reminder

- Do not store secrets in plain text in the repo. Use secret stores (e.g., Vault), CI/CD secret variables, or environment-specific secret management.
