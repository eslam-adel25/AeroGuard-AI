# Database Schema and Models

The data layer is implemented in backend/app/models/models.py and initialized through backend/app/database/session.py.

Storage behavior

- The application uses SQLAlchemy with a database connection string from DATABASE_URL.
- The code supports SQLite-style URLs as well as PostgreSQL-style URLs, but the models and dialect types are PostgreSQL-oriented.
- The schema is created on startup with Base.metadata.create_all(bind=engine); there is no Alembic migration setup in the repository.

Core tables

- roles — stores role names such as Officer and Administrator.
- users — stores account metadata, password hash, profile information, verification state, and role linkage.
- system_settings — stores global defaults such as detection confidence, GPU usage, frame skip, and AI rule toggles.
- cameras — stores stream source, camera type, owner, and status.
- restricted_zones — stores polygon zones for each camera.
- detections — stores per-detection records, confidence, priority, and violation flags.
- email_verifications — stores tokens and OTP data for email verification.
- refresh_tokens — stores refresh tokens with expiry and revocation state.
- activity_logs — stores activity events for auditing and profile history.
- user_settings — stores user-specific UI and AI preferences.
- reports — stores generated report metadata and export history.
- trackings — stores tracking state for detections across frames.
- ai_events — stores alert events associated with a camera and optional track.

Important implementation notes

- UUIDs are represented using a custom GUID type that works with PostgreSQL UUIDs and falls back to a string form for other dialects.
- JSON fields are used for zone coordinates, report payloads, and event metadata.
- The camera and AI event relationships are owner-scoped for access checks.

Refer to backend/app/models/models.py for the full schema and field list.
