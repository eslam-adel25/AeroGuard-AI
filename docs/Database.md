# Database Schema and Models

The data layer is implemented in backend/app/models/models.py and initialized through backend/app/database/session.py.

Storage behavior

- The application uses SQLAlchemy with a database connection string from DATABASE_URL.
- The code supports SQLite-style URLs as well as PostgreSQL-style URLs, but the models and dialect types are PostgreSQL-oriented.
- Alembic revisions are maintained in the repository root under alembic/versions.
- Startup also calls Base.metadata.create_all(bind=engine), which creates missing tables but does not replace migrations for existing databases.

Core tables

- roles — stores role names such as Owner, Administrator, and Officer. Owner is distinct from Administrator.
- users — stores account metadata, password hash, profile information, verification state, role linkage, and nullable customer_profile_id membership for Admin/Officer users.
- customer_profiles — stores each customer's workflow and access states, optional camera quota, feature entitlement flag, historical activation date, and Owner notes. The activation date remains nullable and is no longer configured through the Owner workflow.
- customer_feature_permissions — stores per-customer feature grants or denials, unique by profile and feature key.
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
- Customer-resource access is tenant-scoped for Admin/Officer users and
  platform-wide only for the database-backed Owner role.
- CustomerProfile is the canonical tenant identity. Camera, zone, detection,
  tracking, AI-event, report, and user-settings rows have nullable
  customer_profile_id columns; camera-child composite foreign keys prevent
  new rows from linking to a camera under a different tenant.
- New Admin registrations create one independent pending CustomerProfile and
  are linked to it. Admin-created Officers share that profile and do not create
  profiles of their own. Owner is platform-wide and has no customer profile.
- Migration 006 adds nullable membership and ownership columns, indexes, and
  camera-child consistency constraints; it does not backfill or reassign legacy
  records. It has been validated on staging only and has not been run in
  production. Ambiguous Officer and report ownership must be mapped and
  explicitly approved before any production backfill.
- A NULL camera quota remains unlimited for migrated legacy customers; a configured zero is a distinct limit. Legacy profiles retain all-feature eligibility without changing global or user settings.
- Migration 004's legacy backfill follows `REQUIRE_EMAIL_VERIFICATION` and excludes only the literal `Administrator` role. Existing `Admin` role users are eligible customers and remain distinct from the `Owner` role.
- Migration 003 sets every NULL or non-60 `abandoned_bag_seconds` in `system_settings` and `user_settings` to 60. For legacy adoption where saved values must be preserved, capture both tables by primary key (and user settings by `owner_id`) before upgrading from revision 002; migration 005 restores and verifies those exact values in the same transaction, then removes the temporary snapshots. Revision 005 fails closed if rows exist without snapshots; a new database with both settings tables empty needs no snapshots.
- Customer workflow state and account access state are independent. API access enforces the active customer workflow. Activation enables all six implemented customer-level features; legacy active `PLATFORM_CUSTOMER` profiles receive the same effective access without rewriting historical permission rows. Global AI module settings, account lifecycle restrictions, and resource ownership checks remain independent.
- Migration 004 creates the `Owner` role once and adds a partial unique index on `users.role_id` for that role, allowing at most one Owner user without constraining other roles.
- Self-registered users begin with a pending profile. Email verification moves the workflow to `UNREAD`, but customer API access remains blocked until activation changes the profile to `PLATFORM_CUSTOMER` and `ACTIVE`.
- The secure Owner provisioning command requires the migration-created single-Owner index and does not create a customer profile for the Owner account.

Refer to backend/app/models/models.py for the full schema and field list.
