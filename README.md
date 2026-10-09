<div align="center">

<img src="docs/assets/logo.png" alt="AeroGuard AI Logo" width="160" />

# AeroGuard AI

<img src="docs/assets/technology-stack.svg" alt="AeroGuard AI technology stack grouped by languages, frontend, backend, AI and vision, database, APIs and security, reporting, and development tools" width="100%" />

**Camera monitoring, AI-assisted detection, event review, and operational reporting**

A full-stack computer vision platform integrating FastAPI, OpenCV, and Ultralytics YOLO with a React/TypeScript operations dashboard.

---

</div>

AeroGuard AI is a full-stack application with a FastAPI backend and a React/TypeScript frontend. It manages RTSP streams, uploaded video files, and local OpenCV camera inputs; executes object detection and configured spatial/behavioral camera rules; persists detection and alert records; and provides live monitoring, event review, analytics, and operational report exports.

> [!IMPORTANT]
> **Implementation Scope & Status**: This document details the implementation present in this codebase, not a prospective product roadmap or certified production deployment. Review [Security and limitations](#security-and-limitations) prior to exposing any instance to an external network.

---

## Table of Contents

- [Capability Status](#capability-status)
- [System Architecture](#system-architecture)
- [Repository Map](#repository-map)
- [Frontend Application](#frontend-application)
  - [Navigation and Pages](#navigation-and-pages)
  - [API Client and Local State](#api-client-and-local-state)
  - [Notifications and Real-Time Feeds](#notifications)
- [Backend Application](#backend-application)
  - [Application and Database Startup](#application-and-database-startup)
  - [Router and Service Responsibilities](#router-and-service-responsibilities)
- [Camera Sources and Lifecycle](#camera-sources-and-lifecycle)
  - [Supported Source Types](#supported-source-types)
  - [Start, Stop, and Worker Lifecycle](#start-stop-and-worker-lifecycle)
  - [Camera Zones and Streams](#camera-zones-and-streams)
- [AI Processing and Rules](#ai-processing-and-rules)
  - [Frame Pipeline](#frame-pipeline)
  - [Tracking and Per-Camera State](#tracking-and-per-camera-state)
  - [Detection Records vs. Alert Events](#detection-records-versus-alert-events)
  - [Implemented Rule Paths](#implemented-rule-paths)
- [Events, Alarms, and Screenshots](#events-alarms-and-screenshots)
  - [Event Lifecycle](#event-lifecycle)
  - [Screenshot Persistence](#screenshot-persistence)
  - [Alarm State](#alarm-state)
- [WebSocket Protocol](#websocket-protocol)
  - [Connection](#connection)
  - [Message Types and Specifications](#messages-observed-in-the-implementation)
- [Database and Persistence](#database-and-persistence)
  - [Entity Model Reference](#database-and-persistence)
  - [Storage Boundaries](#storage-boundaries)
- [Analytics and Reports](#analytics-and-reports)
  - [Data Source and Filters](#data-source-and-filters)
  - [Stored Reports and Export Formats](#stored-reports-and-export-formats)
- [HTTP API Reference](#http-api-reference)
  - [Authentication — `/auth`](#authentication--auth)
  - [Users — `/users`](#users--users)
  - [Cameras — `/cameras`](#cameras--cameras)
  - [AI Events — `/ai/events`](#ai-events--aievents)
  - [Reports and Settings](#reports-and-settings)
- [Authentication and Authorization](#authentication-and-authorization)
  - [Access and Refresh Tokens](#access-and-refresh-tokens)
  - [Roles and Ownership](#roles-and-ownership)
- [Configuration Reference](#configuration-reference)
  - [Backend Environment](#backend-environment)
  - [Frontend Environment](#frontend-environment)
- [Install and Run Locally](#install-and-run-locally)
  - [Prerequisites](#prerequisites)
  - [Backend Setup](#backend-setup)
  - [Frontend Setup](#frontend-setup)
  - [Running Together](#running-together)
  - [Production-Oriented Command Example](#production-oriented-command-example)
- [Dependencies and Scripts](#dependencies-and-scripts)
  - [Technology Stack](#technology-stack)
  - [Backend Dependencies](#backend-dependencies)
  - [Frontend Dependencies and Scripts](#frontend-dependencies-and-scripts)
- [Tests and Quality Checks](#tests-and-quality-checks)
- [Troubleshooting](#troubleshooting)
- [Security and Limitations](#security-and-limitations)
- [Documentation Index](#documentation-index)
- [Contributing](#contributing)

---

## Capability Status

The following matrix documents the operational readiness of features in the current codebase.

| Functional Area | Current Implementation Status | Architectural Notes |
| :--- | :--- | :--- |
| **User Authentication** | Implemented | Registration, login, access tokens, refresh tokens, password hashing via bcrypt (12 rounds). |
| **Email Verification** | Optional | Controlled via `REQUIRE_EMAIL_VERIFICATION`; requires functional SMTP configuration for external transmission. |
| **Camera Management** | Implemented | Validated for RTSP/RTSPS network streams, uploaded video files, and backend OpenCV device index `0`. |
| **Object Detection & Inference** | Implemented | Runs in the backend process using a shared YOLO model with per-camera runtime isolation. |
| **Spatial & Behavioral Rules** | Implemented | Restricted areas, tripwire/direction vectors, loitering detection, and baggage ownership rules present in processor. |
| **Hazard Alerts (Fire / Smoke)** | Implemented (Gated) | Code paths exist and are gated by user settings; dependent on labels emitted by the configured model weights. |
| **Crowd Density & Advanced Settings** | Partial | Settings schema and UI controls exist; not all configuration fields are consumed by the runtime engine. |
| **Real-Time Telemetry & Alarms** | Implemented | Dispatched over the dashboard WebSocket; note that audience isolation filtering varies by message type. |
| **Reporting & Export Pipeline** | Implemented | Aggregated from relational detection records; supports JSON snapshots, PDF, CSV, and Excel exports. |


> [!NOTE]
> The designation **Implemented** reflects executable code paths. It does not constitute a guaranteed detection accuracy threshold or service-level agreement (SLA). Environmental visibility, model class mapping, zone definitions, and host hardware resources directly dictate operational behavior.

---

## System Architecture

The following diagram illustrates data flow and boundary interactions between the presentation client, API layer, runtime inference workers, and storage tiers.

```mermaid
flowchart LR
    subgraph Client ["Frontend Client"]
        Browser["React Application (Vite)"]
    end

    subgraph API_Layer ["Application & Transport Layer"]
        API["FastAPI Routers (/api/v1)"]
        WS["WebSocket Endpoint (/ws/dashboard)"]
        Auth["JWT & Ownership Verification"]
    end

    subgraph Engine ["Runtime Engine"]
        Runtime["In-Process AIProcessor Singleton"]
        Capture["OpenCV VideoCapture"]
        YOLO["Ultralytics YOLO (Shared Model Lock)"]
        Tracker["Camera-Scoped Tracker & Rule State"]
    end

    subgraph Storage ["Persistence & Filesystem"]
        DB[("PostgreSQL Database")]
        Uploads["Static Uploads (backend/uploads)"]
    end

    Browser -->|HTTP REST Requests| API
    Browser <-->|Bi-directional WebSocket| WS
    API --> Auth
    API --> DB
    API -->|Reserve, Start, Stop| Runtime
    Runtime --> Capture
    Capture -->|Decoded Frames| Runtime
    Runtime -->|Locked Inference Calls| YOLO
    Runtime --> Tracker
    Runtime -->|Detection & AIEvent Inserts| DB
    Runtime -->|Alarm, Camera, & AI Telemetry| WS
    Runtime -->|Event Screenshots & Uploads| Uploads
    API -->|Authenticated MJPEG Stream| Browser
    WS -->|JSON Broadcast Messages| Browser
```

### Architectural Mechanics

1. **Routing and API Structure**: FastAPI mounts HTTP routers beneath `/api/v1` alongside the persistent `/ws/dashboard` WebSocket endpoint. Database sessions are managed through scoped SQLAlchemy providers.
2. **Lifecycle and Schema Validation**: Application startup triggers table creation via ORM metadata, executes a PostgreSQL catalog compatibility routine, and binds the AI processor singleton to the settings service.
3. **In-Process Inference Engine**: Initialized as a singleton in `backend/app/ai/processor.py`. Camera ingestion workers run as background tasks within the primary backend process.
   - *State Volatility*: Workers are not persistent background daemons. A backend process restart terminates running workers and purges in-memory tracker states, alarm flags, and person identity sessions.
   - *Concurrency Model*: The YOLO model instance is shared across all active streams; inference passes are protected by a threading lock. Ingestion, tracking, loitering timers, and spatial rules maintain strict per-camera isolation.
4. **Client Proxying**: In local development, Vite proxies `/api`, `/ws`, and `/uploads` directly to FastAPI. The Axios HTTP client attaches bearer tokens via headers, while WebSocket sessions authenticate via query string parameters.

---

## Repository Map

The source tree is divided into an isolated FastAPI backend service, a React/TypeScript frontend client, and root-level database migration configurations.

```text
.
├── alembic.ini                   # Alembic migration configuration
├── alembic/                      # Database revision scripts
│   ├── env.py
│   └── versions/
├── backend/
│   ├── app/
│   │   ├── ai/                   # Inference routines, trackers, person identity, ownership logic
│   │   ├── api/v1/               # HTTP endpoints (auth, users, cameras, events, reports, settings, WS)
│   │   ├── core/                 # JWT security, middleware routines, SMTP email delivery
│   │   ├── database/             # SQLAlchemy engine, session yields, schema compatibility helpers
│   │   ├── models/               # SQLAlchemy ORM entity definitions
│   │   ├── repositories/         # Query abstractions and database persistence handlers
│   │   ├── schemas/              # Pydantic request and response schemas
│   │   ├── services/             # Domain logic (AI events, reporting, user settings, threat evaluator)
│   │   ├── utils/                # PDF report generators and device utility helpers
│   │   └── websocket/            # Authenticated connection manager and broadcast router
│   ├── uploads/                  # Runtime storage for uploads, videos, and event captures
│   ├── models/
│   │   └── yolov8n.pt            # Default YOLO weights file resolved by the AI processor
│   ├── tests/                    # Backend automated test suite
│   ├── requirements.txt          # Python runtime dependencies
│   └── runtime.txt               # Pinned Python version (3.12.10)
├── docs/                         # Extended technical documentation and architecture specs
├── frontend/
│   ├── public/                   # Static frontend assets
│   ├── src/
│   │   ├── components/           # Reusable UI controls and navigation layouts
│   │   ├── i18n/                 # Localization dictionaries and i18next configuration
│   │   ├── pages/                # Top-level operational views and workflows
│   │   ├── services/             # Axios API client, WebSocket singleton, notification adaptors
│   │   └── assets/               # Local style sheets and graphic assets
│   ├── package.json              # Client dependencies and execution scripts
│   ├── package-lock.json         # Pinned npm dependency tree
│   └── vite.config.ts            # Vite bundler, plugin, and proxy configuration
└── README.md
```

### Core Backend Modules

| Module Path | Core Responsibilities |
| :--- | :--- |
| `backend/app/main.py` | Application factory, lifecycle hooks, static `/uploads` mounting, CORS policies, security headers, and router registrations. |
| `backend/app/database/session.py` | Environment loading (`backend/.env`), SQLAlchemy engine configuration, session generators, and startup schema verification. |
| `backend/app/models/models.py` | ORM entity definitions, foreign key constraints, indexes, and relationship graphs. |
| `backend/app/api/v1/cameras.py` | Camera provisioning, stream validation, worker start/stop endpoints, zone geometry, and authenticated MJPEG feeds. |
| `backend/app/ai/processor.py` | Worker lifecycle, frame decoding, inference lock coordination, tracking integration, rule evaluation, and alarm state dispatch. |
| `backend/app/ai/tracker.py` | Greedy IoU tracking engine and adapter abstraction for optional external trackers. |
| `backend/app/ai/identity.py` | In-memory session identity registry used during active stream analysis. |
| `backend/app/services/ai_service.py` | Event registration, disk screenshot persistence, and `ai_event` WebSocket broadcasts. |
| `backend/app/api/v1/websocket_api.py` | Dashboard WebSocket authentication handshake and initial authorized alarm snapshot assembly. |
| `backend/app/websocket/manager.py` | Active socket registry, audience scoping logic, and network message delivery. |
| `backend/app/services/report_service.py` | Detection query filtering, summary metric aggregation, and report payload composition. |
| `backend/app/utils/report_generator.py` | Programmatic PDF layout, data table composition, and file output. |

### Core Frontend Modules

| Module Path | Core Responsibilities |
| :--- | :--- |
| `frontend/src/App.tsx` | Authenticated application container, view state switching, notification listener, and session termination. |
| `frontend/src/components/Sidebar.tsx` | Primary navigation control supporting operational dashboard views. |
| `frontend/src/pages/Dashboard.tsx` | Primary operations center: live stream viewing, PTZ/worker controls, zone overlays, alarm banners, and camera telemetry. |
| `frontend/src/pages/Cameras.tsx` | Ingestion source provisioning (LIVE, UPLOAD, USB), camera lifecycle management, and stream deletion. |
| `frontend/src/pages/Analytics.tsx` | Temporal/camera filtering, metric visualizations, detection breakdown, and on-demand PDF report compilation. |
| `frontend/src/pages/AlertHistory.tsx` | Historical AI event viewer with tabular sorting and screenshot review modal. |
| `frontend/src/pages/Profile.tsx` | User profile modifications, credential rotation, avatar upload, and active session termination. |
| `frontend/src/pages/Settings.tsx` | User preference management (confidence thresholds, frame skipping, audio/visual alerts, notification rules). |
| `frontend/src/pages/Reports.tsx` | Standalone report viewer component (the active UI routes the `"reports"` key to `Analytics.tsx`). |
| `frontend/src/services/api.ts` | Axios instance initialization, request token interceptor, and typed service endpoints. |
| `frontend/src/services/socket.ts` | Singleton WebSocket client, typed message dispatching, and subscriber multiplexing. |
| `frontend/src/services/notificationService.ts` | Historical event fetching and real-time socket event bridge for notification toasts. |
| `frontend/src/i18n/` | Internationalization dictionary initialization supporting English and Arabic translations. |

---

## Frontend Application

### Navigation and Pages

The application shell uses a state-driven navigation router keyed to the sidebar state rather than independent browser paths for each authenticated view.

| View Key | Component | Primary Operational Workflow |
| :--- | :--- | :--- |
| `dashboard` | `Dashboard` | Select active camera, monitor live stream/telemetry, toggle worker lifecycle, configure polygonal zones, and review active alarms. |
| `cameras` | `Cameras` | Register new camera sources (`LIVE`, `UPLOAD`, `USB`), review source health, start/stop ingestion, and delete camera records. |
| `reports` | `Analytics` | Filter historical detection metrics, view analytical distributions, and trigger PDF report compilation. |
| `alerts` | `AlertHistory` | Paginated review of historical `AIEvent` entities with integrated screenshot modal viewing. |
| `users` | `Profile` | Self-service profile updates, password changes, avatar uploads, and active refresh-token session invalidation. |
| `settings` | `Settings` | Inspect, update, and reset user-level detection parameters and notification preferences. |

> [!NOTE]
> **Localization and Text Direction**: The client includes translation dictionaries for English (`en`) and Arabic (`ar`), stored in `localStorage` under `ag_language`. Both configurations force `document.documentElement.dir = "ltr"`; the interface does not implement right-to-left (RTL) styling.

### API Client and Local State

- **Authentication Header Injection**: The centralized Axios client targets `/api/v1` and retrieves `ag_token` from browser `localStorage`. If the token is missing or malformed, it is pruned. Outgoing requests include an `Authorization: Bearer <token>` header.
- **Client-Side State Storage**: User state, active alarms, and system metrics are held in React context and component hooks. Browser storage holds preferences only. Tokens are not managed via `HttpOnly` cookies in the current implementation.
- **Service Layer Abstractions**:
  - `cameraService`: Stream registration, worker lifecycle controls, deletion, and zone mutations.
  - `aiService`: Event queries, read marker mutations, and binary screenshot downloads.
  - `reportService`: Analytical aggregation queries, snapshot creation, and file exports (CSV, Excel, PDF).
  - `settingsService`: User configuration retrieval, updating, and resetting.

### Notifications

- **Event History Fetching**: The notification panel retrieves up to 50 historical entries from `/api/v1/ai/events` upon initialization.
- **Live Stream Bridge**: Real-time `ai_event` messages dispatched over `/ws/dashboard` append directly to the active notification feed.
- **Legacy Fallback Note**: The client notification service contains a fallback to a legacy `/notifications/` route upon failure. Because the backend does not register `/notifications/`, this fallback will fail if triggered.
- **Screenshot Access**: Event screenshots are retrieved through `/api/v1/ai/events/{event_id}/screenshot` as binary blobs and converted to local object URLs. Screenshots are unavailable for events while pending capture or if capture was skipped.

---

## Backend Application

### Application and Database Startup

The backend entry point in `backend/app/main.py` coordinates initialization through the following sequence:

1. **Static Filesystem Mount**: Mounts `backend/uploads` directly to `/uploads` to serve static assets.
2. **Metadata Synchronization**: Executes `Base.metadata.create_all(bind=engine)` against the configured database.
3. **Compatibility Verification**: Runs `_ensure_schema_compatibility()` to inspect PostgreSQL catalogs for expected table structures and columns.
4. **Engine Registration**: Binds the `AIProcessor` singleton reference to the user settings service so setting updates notify the running engine.
5. **Router Registration**: Registers all core REST controllers under `/api/v1` and attaches the WebSocket controller at `/ws/dashboard`.

> [!WARNING]
> **Database Migrations and Engine Compatibility**:
> - The startup schema compatibility routine relies on PostgreSQL catalog tables (`information_schema`). While SQLite fallback branches exist in `session.py`, PostgreSQL is strictly required for full operation and reporting.
> - `create_all()` will not alter existing columns or apply complex schema diffs. Always maintain and execute Alembic revisions (`alembic upgrade head`) and perform database backups before updating production environments.

### Router and Service Responsibilities

- **Authentication (`auth.py`)**: Registration, credential verification, JWT issuance, refresh-token rotation, OTP verification, and session logout.
- **User Management (`users.py`)**: Current user profile mutations, credential rotation, avatar upload, session inspection, and administrator user administration.
- **Camera Controller (`cameras.py`)**: Ingestion source validation, zone management, worker lifecycle dispatching, and authenticated MJPEG stream encoding.
- **AI Event Controller (`ai.py`)**: Event pagination, read status tracking, manual event entry, and secured screenshot file delivery.
- **Reporting Engine (`reports.py`)**: Detection analytics aggregation, persistent report snapshot generation, and multi-format exports (PDF, CSV, Excel).
- **Configuration (`settings.py`)**: User-level detection sensitivity, frame skipping, and hazard toggles; propagates changes to the active inference engine.
- **Inference Runtime (`processor.py`)**: Video decoding, frame queueing, lock-protected YOLO execution, tracking state management, and telemetry broadcasting.
- **Repositories**: Standardized data access layer encapsulating raw SQLAlchemy queries to prevent domain logic leakage.

---

## Camera Sources and Lifecycle

### Supported Source Types

| Ingestion Type | Provisioning Verification | Runtime Execution Mechanics |
| :--- | :--- | :--- |
| `LIVE` | Validates `rtsp://` or `rtsps://` scheme and probes endpoint for decodable frames. | Opens persistent RTSP network stream via OpenCV `VideoCapture`. |
| `UPLOAD` | Validates extensions (`.mp4`, `.mov`, `.avi`, `.mkv`, `.webm`) and 200 MiB file ceiling. | Saves file to `backend/uploads/videos/` and reads as local file input. |
| `USB` | Overrides input string to `"0"`. | Binds to OpenCV device index `0` on the host operating system. |

### Start, Stop, and Worker Lifecycle

The ingestion worker lifecycle relies on cooperative cancellation flags and reservation states:

```mermaid
sequenceDiagram
    autonumber
    participant UI as Dashboard / Cameras UI
    participant API as POST /cameras/{id}/start
    participant Engine as AIProcessor Singleton
    participant Worker as Camera Worker Thread
    participant DB as PostgreSQL Database

    UI->>API: Start request (Authorization: Bearer <token>)
    API->>API: Validate JWT and verify camera ownership
    API->>Engine: Reserve camera startup slot
    API->>API: Probe RTSP source if type is LIVE
    API->>Engine: Activate startup reservation
    API->>DB: Persist Camera status as 'Processing'
    API->>Worker: Dispatch process_camera via BackgroundTasks
    API-->>UI: Return HTTP 200 (Scheduled)
    
    Worker->>Worker: Open VideoCapture, allocate tracker state
    Worker->>DB: Record detections and alert events
    Worker-->>UI: Broadcast 'Running' & telemetry via WebSocket
    
    UI->>API: Stop request: POST /cameras/{id}/stop
    API->>Engine: Set cooperative stop flag and set status 'Offline'
    Worker->>Worker: Detect stop flag, exit frame loop
    Worker-->>UI: Broadcast 'Offline' and clear active alarms
    Worker->>Engine: Release VideoCapture and purge in-memory state
```

#### Lifecycle Characteristics

1. **Reservation Locking**: The start endpoint registers an internal reservation before probing external streams. Duplicate start requests for an active camera are rejected, while an already-running camera returns immediately.
2. **Cancellation Handling**: If a stop command is issued while a camera is still probing, the reservation is canceled and the background task exits before opening the stream.
3. **Asynchronous Dispatch**: The HTTP response confirms that the worker was *scheduled* via FastAPI `BackgroundTasks`. The camera status initially transitions to `Processing`, followed by `Running` once the first frame decodes successfully.
4. **State Reconciliation**: The `GET /cameras/` endpoint overlays the processor's in-memory status onto database records. If the database indicates `Processing` but no active worker exists, the API reports `Offline`.
5. **Cooperative Teardown**: Stopping a camera does not forcefully abort threads. The API raises a flag that the frame-processing loop checks each cycle. When detected, the worker releases the capture handle, clears tracker memory, and dispatches an `Offline` status over the WebSocket.

### Camera Zones and Streams

- **Polygonal Zone Definitions**: Spatial detection zones are stored in `RestrictedZone` records as normalized coordinate arrays. Coordinates are converted to pixel space by the processor during frame evaluation.
- **MJPEG Streaming**: `GET /cameras/{camera_id}/stream` yields a multipart MJPEG stream generated on the fly from the latest annotated frame cached in memory. The endpoint validates camera ownership prior to streaming.
- **Resource Deletion**: Deleting a camera stops the worker, deletes uploaded video files from `backend/uploads/videos/` (if within the uploads tree), and removes associated zones, detections, events, and tracking rows before deleting the camera record.

---

## AI Processing and Rules

### Frame Pipeline

The inference loop executes sequentially for each decoded frame within a worker thread:

```text
[Camera Stream / File Source]
            │
            ▼
   1. Frame Decoding (OpenCV)
            │
            ▼
   2. Frame Skipping Evaluation (per user settings)
            │
            ▼
   3. YOLO Inference (Protected by global threading lock)
            │
            ▼
   4. Bounding Box & Label Extraction (confidence filtered)
            │
            ▼
   5. Tracking & Identity Update (IoU tracking + session identity)
            │
            ▼
   6. Rule Evaluation (Restricted zones, tripwires, loitering, baggage)
            │
            ▼
   7. Visual Overlays & Persistence (Detections & AIEvent insertion)
            │
            ▼
   8. Telemetry & Alarm Broadcast (WebSocket notifications)
            │
            ▼
   9. Frame Cache Update (Held in memory for MJPEG stream)
```

The runtime relies on PyTorch, Ultralytics YOLO, OpenCV, and NumPy. Weights are loaded during application initialization. If weight loading fails, the error is logged and `ai_engine` is set to `None`, causing subsequent camera start calls to return a service-unavailable error.

### Tracking and Per-Camera State

- **Tracker Implementation**: The default tracker is a greedy Intersection-over-Union (IoU) tracker. It matches current bounding boxes to existing tracks above an overlap threshold, registers new track IDs for unmatched boxes, and purges tracks after exceeding a lost-frame limit.
- **Adapter Extensibility**: Facades exist to support external tracking engines (such as ByteTrack or DeepSORT) if installed in the environment. If unavailable, the engine falls back to the IoU tracker.
- **State Isolation**: Movement trajectories, loitering timers, baggage association links, person identity caches, and alarm states are isolated per camera ID.
- **Tracking Table Usage**: While a `Tracking` database table exists in the schema, per-frame track coordinates are maintained strictly in memory and are not written to disk on every frame.

### Detection Records versus Alert Events

The processing pipeline separates analytical metrics from operational alerts:

- **`Detection` Records**: Generated for recognized objects subject to a per-track/per-class cooldown. These records provide raw counts, priority distributions, and violation tracking for analytical dashboards and reports.
- **`AIEvent` Records**: Generated when a specific spatial or behavioral rule threshold is breached. These entities store event severity, confidence, track IDs, detection metadata, read state, and an optional screenshot path.
- **Priority Mapping**: The `build_detection_record` helper maps threat statuses to detection priorities:
  - `DANGER` maps to `Critical` priority and marks `is_violation = True`.
  - `WARNING` maps to `High` priority and marks `is_violation = True`.
  - Standard detections default to `Medium` priority.

### Implemented Rule Paths

```mermaid
flowchart TD
    Detections["Decoded Detections"] --> Filter["Apply Confidence Threshold"]
    Filter --> Trackers["Update Camera Tracker"]
    
    Trackers --> ZoneRule{"Restricted Area?"}
    ZoneRule -- "Box inside polygon" --> AlertZone["Raise Restricted Area Alert"]
    
    Trackers --> TripRule{"Tripwire / Direction?"}
    TripRule -- "Crosses line / vector" --> AlertTrip["Raise Tripwire / Vector Alert"]
    
    Trackers --> LoiterRule{"Loitering Check?"}
    LoiterRule -- "Time > threshold" --> AlertLoiter["Raise Loitering Alert"]
    
    Trackers --> BagRule{"Baggage Ownership?"}
    BagRule -- "Unattended > timeout" --> AlertBag["Raise Abandoned Bag Alert"]
    
    Trackers --> HazardRule{"Fire / Smoke Labels?"}
    HazardRule -- "Model class match" --> AlertHazard["Raise Hazard Alert"]
```

1. **Restricted Areas**: Validates object centroids or bounding boxes against configured polygon zones when restricted-area rules are active.
2. **Tripwire and Directional Vectors**: Analyzes historical track centroids against directional thresholds and boundary vectors.
3. **Loitering Detection**: Tracks person dwell times within bounded coordinates; raises warnings once the configured loiter duration is exceeded.
4. **Baggage Ownership**: Associates detected baggage items with proximate person tracks across consecutive frames based on spatial distances defined in `ownership_config.py`.
5. **Abandoned / Unattended Baggage**: Tracks item separation from associated owners; triggers an alert when distance and temporal thresholds (`abandoned_bag_seconds`) are exceeded.
6. **Fire and Smoke Detection**: Gated by user configuration; triggers when the underlying model emits fire, flame, or smoke classifications.

> [!NOTE]
> The utility `DecisionEngine.evaluate_threat()` maps labels to severity values, but it does not serve as a universal classification engine for all rules. Additionally, while crowd density fields exist in settings schemas, the active worker does not currently implement a crowd density alert rule.

---

## Events, Alarms, and Screenshots

### Event Lifecycle

When an alert condition occurs, `AIService.register_event()` persists an `AIEvent` row and broadcasts an `ai_event` message over the WebSocket. An internal debounce key prevents duplicate event creation for the same trigger across consecutive frames.

The REST API allows clients to query historical events, inspect event details, toggle read states, insert manual events, and download attached screenshots.

### Screenshot Persistence

- **Storage Location**: Alert frames are stored under `backend/uploads/ai_events/`.
- **Capture Latency**: Some alert workflows create an initial `AIEvent` with a pending screenshot flag, then capture and write a JPEG frame once the alert condition persists for at least 5 seconds.
- **Notification Updates**: When a screenshot is attached to an existing event, an updated `ai_event` message is broadcast over the WebSocket containing the image URL.
- **Authorization Context**: While `GET /ai/events/{event_id}/screenshot` enforces camera ownership checks, the underlying storage directory is also mounted directly at `/uploads`.

### Alarm State

Alarm states represent active operational conditions managed in memory:

- **State Representation**: Keyed by `camera_id`, indicating whether an alarm is `active` and listing triggering sources (e.g., `["RESTRICTED AREA"]`).
- **State Broadcasts**: Transition updates are broadcast as `alarm_state` messages whenever an alarm activates or clears.
- **Teardown Cleanup**: If a worker terminates while an alarm is active, the engine automatically dispatches an inactive state update.
- **Decoupled Records**: Clearing an active alarm has no effect on historical `AIEvent` records, which remain stored in the database.

---

## WebSocket Protocol

### Connection

Establish an authenticated WebSocket connection by supplying a valid JWT access token in the query string:

```text
ws://localhost:8000/ws/dashboard?token=<JWT_ACCESS_TOKEN>
```

When operating behind TLS reverse proxies, connect via `wss://`.

Upon successful connection, the server validates the token and transmits an initial `alarm_state_snapshot` message containing all cameras the user is authorized to view:

```json
{
  "event": "alarm_state_snapshot",
  "data": {
    "states": {
      "c8b6f3a1-2d4e-4e6a-8b9c-0d1e2f3a4b5c": {
        "active": true,
        "sources": [
          "RESTRICTED AREA"
        ]
      }
    }
  }
}
```

### Messages Observed in the Implementation

| Event Type | Payload Fields | Purpose and Dispatch Rules |
| :--- | :--- | :--- |
| `alarm_state_snapshot` | `states` (dictionary of camera IDs containing `active` and `sources`) | Sent to newly connected clients to establish baseline alarm state. |
| `alarm_state` | `camera_id`, `active`, `sources` | Emitted on alarm state transitions. Filtered by camera ownership. |
| `camera_status` | `camera_id`, `status` (`Processing`, `Running`, `Offline`) | Emitted on worker lifecycle changes. Broadcast globally to all connections. |
| `ai_status` | `camera_id`, `fps`, `objects_count`, `persons_count`, `bags_count`, `cars_count`, `critical_alerts` | Real-time processing telemetry. Broadcast globally to all connections. |
| `ai_event` | `event_id`, `camera_id`, `detection_type`, `severity`, `confidence`, `timestamp`, `screenshot_path` | Dispatched when an alert is created or updated. Filtered by camera ownership. |

> [!CAUTION]
> **Audience Isolation Notice**: The connection manager enforces ownership checks on `ai_event` and `alarm_state` messages. However, `camera_status` and `ai_status` updates are broadcast to **all** connected WebSockets. Take this into account when designing multi-tenant deployments.

---

## Database and Persistence

Relational data is stored in PostgreSQL using SQLAlchemy ORM entities with UUID primary keys and JSON/JSONB metadata columns.

| Model | Schema Role and Description |
| :--- | :--- |
| `Role` | User role definition (e.g., `Administrator`, `Officer`). |
| `User` | User accounts, hashed passwords, verification state, and profile references. |
| `Camera` | Camera configurations, stream URLs, storage paths, source types, and owner bindings. |
| `RestrictedZone` | Polygonal coordinate sets and video dimension references tied to a specific camera. |
| `Detection` | Analytical records storing detected object class, priority, confidence, and violation flags. |
| `AIEvent` | Operational alert events with severity, confidence, track references, and screenshot paths. |
| `Tracking` | Durable tracking entity model (not utilized for routine per-frame tracking state). |
| `Report` | Stored report records containing filter parameters, summary metrics, charts, and export histories. |
| `UserSettings` | Per-user application settings, sensitivity thresholds, frame skipping, and alert toggles. |
| `RefreshToken` | Refresh token strings, expiration timestamps, revocation flags, and client device metadata. |
| `EmailVerificationToken` | One-time password (OTP) codes and verification tokens for account activation and email updates. |
| `ActivityLog` | Audit log of administrative actions, user logins, and profile changes. |

### Storage Boundaries

```text
[ PostgreSQL Database ]
  ├── User credentials & RBAC roles
  ├── Camera configurations & polygonal zones
  ├── Detection analytical records
  ├── Persistent AI alert events
  ├── Stored report snapshots & audit logs
  └── Refresh tokens & verification codes

[ Process Memory (Volatile) ]
  ├── Ingestion VideoCapture handles
  ├── Active track states & lost-frame counters
  ├── Loitering timers & spatial movement history
  ├── Baggage ownership association links
  └── Active camera alarm state flags

[ Host Filesystem (backend/uploads) ]
  ├── videos/      -> Uploaded video source files
  ├── ai_events/   -> Alert frame JPEG screenshots
  └── reports/     -> Compiled PDF export documents
```

---

## Analytics and Reports

### Data Source and Filters

The analytics engine aggregates raw `Detection` records rather than relying on `AIEvent` alerts. Queries can filter by date ranges, specific cameras, object classes, priority levels, and confidence intervals. Non-administrator queries are restricted to cameras owned by the requesting user.

The service calculates:

- Overall detection counts, total violations, priority distributions, and active camera counts.
- Summary statistics for detection confidence (average, minimum, maximum).
- Class distributions and severity groupings.
- Top ten cameras and top ten detected object classes.
- The 20 most recent detection entries.
- Time-series buckets (hourly for 24-hour ranges, daily for up to 7 days, weekly for longer periods).
- A 24-hour activity heatmap based on detection timestamps.
- A camera frequency breakdown exposed under `frequency_by_zone` (grouped by camera name, not by individual polygonal zone).

> [!NOTE]
> Category groupings (person, vehicle, weapon, fire/smoke, suspicious object) are string-matched aggregations rather than separate model classifications. The summary metric combines fire and smoke into a single count while also exposing each value individually.

### Stored Reports and Export Formats

1. **Snapshot Generation**: `POST /reports/generate` runs the aggregation query and saves the parameters, summaries, and charts into a `Report` record. Subsequent queries read this snapshot directly.
2. **Export Processing**:
  
   - **PDF**: Rendered via `fpdf2` and saved to `backend/uploads/reports/` before being streamed back to the client.

---

## HTTP API Reference

All REST endpoints are prefixed with `/api/v1` except for the WebSocket endpoint at `/ws/dashboard`. Interactive OpenAPI documentation is available at `/docs` and `/redoc`.

### Authentication — `/auth`

| Method & Path | Access Control | Purpose |
| :--- | :--- | :--- |
| `POST /auth/register` | Public (Rate-limited) | Create a new user account (defaults to `Officer` role). |
| `POST /auth/login` | Public (Rate-limited) | Authenticate credentials and receive access and refresh tokens. |
| `POST /auth/refresh` | Refresh Token | Exchange a valid refresh token for a new access token. |
| `GET /auth/verify` | Public Token | Validate an email verification token. |
| `POST /auth/verify-otp` | Public Token | Validate account using email and OTP code. |
| `POST /auth/resend-verification` | Public (Rate-limited) | Resend an account verification message. |
| `POST /auth/logout` | Refresh Token | Revoke the provided refresh token. |
| `GET /auth/create-admin` | **Public** | **Diagnostic endpoint**: Returns total user count and registered usernames. |

> [!WARNING]
> The diagnostic route `GET /auth/create-admin` requires no authentication and exposes existing usernames. Remove or restrict this endpoint before deploying to production.

### Users — `/users`

| Method & Path | Access Control | Purpose |
| :--- | :--- | :--- |
| `GET /users/profile` | Authenticated | Retrieve current user profile details. |
| `PUT /users/profile` | Authenticated | Update current user profile details. |
| `PUT /users/profile/password` | Authenticated | Update current user password. |
| `POST /users/profile/password` | Authenticated | Alternate endpoint for password updates. |
| `POST /users/profile/avatar` | Authenticated | Upload user profile avatar image. |
| `POST /users/profile/change-email` | Authenticated | Initiate an email change verification flow. |
| `GET /users/profile/activity` | Authenticated | Review recent activity log entries for the current user. |
| `GET /users/profile/sessions` | Authenticated | List active refresh-token sessions and client metadata. |
| `POST /users/profile/logout-all` | Authenticated | Invalidate all active refresh tokens for the current user. |
| `GET /users/roles` | Authenticated | List all defined application roles. |
| `GET /users/` | Administrator | List all registered user accounts. |
| `POST /users/` | Administrator | Provision a new user account with a specified role. |
| `DELETE /users/{user_id}` | Administrator | Remove a user account and associated credentials. |

### Cameras — `/cameras`

| Method & Path | Access Control | Purpose |
| :--- | :--- | :--- |
| `POST /cameras/` | Authenticated | Create a camera using multipart form data (name, location, type, URL/file). |
| `GET /cameras/` | Authenticated | List all cameras visible to the current user. |
| `DELETE /cameras/{camera_id}` | Owner / Admin | Stop workers, purge records, delete video files, and remove camera. |
| `POST /cameras/{camera_id}/start` | Owner / Admin | Validate ingestion source, reserve slot, and schedule worker thread. |
| `POST /cameras/{camera_id}/stop` | Owner / Admin | Set cooperative stop flag and mark camera status as `Offline`. |
| `GET /cameras/{camera_id}/stream` | Owner / Admin | Retrieve authenticated MJPEG stream of latest annotated frames. |
| `POST /cameras/{camera_id}/zones` | Owner / Admin | Create a polygonal restricted zone for a camera. |
| `GET /cameras/{camera_id}/zones` | Owner / Admin | Retrieve all defined polygonal zones for a camera. |
| `DELETE /cameras/{camera_id}/zones/{zone_id}` | Owner / Admin | Delete a specific polygonal zone from a camera. |

### AI Events — `/ai/events`

| Method & Path | Access Control | Purpose |
| :--- | :--- | :--- |
| `GET /ai/events` | Authenticated | Paginated query for events, with optional camera and search filters. |
| `GET /ai/events/{event_id}` | Owner / Admin | Retrieve detailed information for a single event. |
| `PATCH /ai/events/{event_id}/read` | Owner / Admin | Mark a specific event as read. |
| `POST /ai/events/read-all` | Authenticated | Mark all visible events as read. |
| `POST /ai/events/manual` | Authenticated | Manually create an event record with optional image upload. |
| `GET /ai/events/{event_id}/screenshot` | Owner / Admin | Download the attached JPEG screenshot for an event. |

### Reports and Settings

| Method & Path | Access Control | Purpose |
| :--- | :--- | :--- |
| `GET /reports/summary` | Authenticated | Retrieve aggregated detection statistics. |
| `GET /reports/dashboard` | Authenticated | Retrieve structured analytical payload for the dashboard. |
| `POST /reports/generate` | Authenticated | Run analytical aggregations and save as a `Report` record. |
| `GET /reports/` | Authenticated | List saved report snapshots with search and pagination. |
| `GET /reports/{report_id}` | Owner / Admin | Retrieve details and charts for a saved report. |
| `DELETE /reports/{report_id}` | Owner / Admin | Delete a saved report record. |
| `GET /reports/export/csv?report_id=...` | Owner / Admin | Export a saved report as a CSV file. |
| `GET /reports/export/excel?report_id=...` | Owner / Admin | Export a saved report as an Excel spreadsheet. |
| `GET /reports/export/pdf?report_id=...` | Owner / Admin | Export a saved report as a compiled PDF document. |
| `GET /settings/` | Authenticated | Retrieve configuration settings for the current user. |
| `PUT /settings/` | Authenticated | Update configuration settings and propagate to the active AI engine. |
| `POST /settings/reset` | Authenticated | Reset configuration settings to default values. |

---

## Authentication and Authorization

### Access and Refresh Tokens

- **Password Hashing**: Passwords are hashed using bcrypt with 12 rounds. A minimum length of 8 characters is enforced during registration and password updates.
- **Access Tokens**: Short-lived JSON Web Tokens signed using HMAC-SHA256 (`HS256`). Payloads contain `user_id`, `role`, `username`, and an `exp` expiration claim (configured via `ACCESS_TOKEN_EXPIRE_MINUTES`, defaulting to 60 minutes).
- **Refresh Tokens**: Randomly generated tokens stored in the `RefreshToken` database table alongside client metadata and a 7-day expiration timestamp.
- **Session Revocation**: Logging out invalidates the provided refresh token. The `/users/profile/logout-all` endpoint revokes all refresh tokens belonging to the user. Requests validate access tokens statelessly without querying the database on every call.
- **Email Verification**: Disabled by default. When enabled via `REQUIRE_EMAIL_VERIFICATION=true`, accounts are created in a pending state until verified. If SMTP variables are not configured, verification tokens are written to the backend application logs instead of being sent via email.

### Roles and Ownership

- **Role Definitions**: Standard registrations are assigned the `Officer` role. Administrative endpoints require the `Administrator` role claim.
- **Resource Ownership**: Camera streams, zones, events, and reports enforce ownership checks against the authenticated user. Administrators are granted access across all resources.
- **WebSocket Access**: Real-time `ai_event` and `alarm_state` messages are scoped to the camera's owner. As noted in the WebSocket section, `camera_status` and `ai_status` updates are broadcast to all connected clients.

---

## Configuration Reference

### Backend Environment

The backend reads configuration settings from `backend/.env` via `backend/app/database/session.py`. `DATABASE_URL` must be set before initializing the database module.

| Environment Variable | Default Value | Description and Operational Guidance |
| :--- | :--- | :--- |
| `DATABASE_URL` | *Required* | SQLAlchemy connection URI. Must target a valid PostgreSQL database. |
| `SECRET_KEY` | Source fallback | Secret key used to sign JWT access tokens. Must be changed in production. |
| `JWT_SECRET` | None | Fallback secret name checked if `SECRET_KEY` is not present. |
| `ALGORITHM` | `HS256` | Cryptographic signing algorithm for JWT tokens. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Lifetime of issued JWT access tokens in minutes. |
| `REQUIRE_EMAIL_VERIFICATION` | `false` | When `true`, requires email verification before account login. |
| `EMAIL_VERIFICATION_EXPIRE_MINUTES`| `15` | Expiration lifetime for email verification tokens and OTP codes. |
| `SMTP_HOST` | None | Hostname for the outbound SMTP mail server. |
| `SMTP_PORT` | `587` | Port for the outbound SMTP mail server. |
| `SMTP_USERNAME` / `SMTP_USER` | None | Authentication username for SMTP delivery. |
| `SMTP_PASSWORD` / `SMTP_PASS` | None | Authentication password for SMTP delivery. |
| `MAIL_FROM` / `EMAIL_FROM` | `no-reply@aeroguard.local` | Sender address used for outgoing email messages. |
| `MAIL_FROM_NAME` | `AeroGuard AI` | Display name used on outgoing email notifications. |
| `FRONTEND_BASE` | `http://localhost:5173` | Base client URL used when generating email verification links. |
| `HOST` | `127.0.0.1` | Network bind address for `python -m app.main`. Blank/wildcard values resolve to loopback. |
| `PORT` | `8000` | Port for `python -m app.main`. |

### Frontend Environment

Frontend settings are loaded by Vite during development and asset compilation.

| Environment Variable | Default Value | Description and Operational Guidance |
| :--- | :--- | :--- |
| `VITE_API_BASE_URL` | `/api/v1` | Base path used by the Axios client. |
| `VITE_WS_BASE_URL` | `window.location.origin` | WebSocket server base URL (client appends `/ws/dashboard?token=...`). |
| `VITE_API_PROXY_TARGET` | `http://127.0.0.1:8000` | Target URL used by the Vite dev server to proxy `/api`, `/ws`, and `/uploads`. |

#### Example `frontend/.env.local`

```dotenv
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_WS_BASE_URL=ws://localhost:8000
VITE_API_PROXY_TARGET=http://127.0.0.1:8000
```

#### Example `backend/.env`

```dotenv
DATABASE_URL=postgresql://aeroguard_user:secure_password@localhost:5432/aeroguard_db
SECRET_KEY=generate-a-strong-random-secret-key-for-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REQUIRE_EMAIL_VERIFICATION=false
```

---

## Install and Run Locally

### Prerequisites

- **Python**: Version `3.12.10` (as defined in `backend/runtime.txt`).
- **Node.js & npm**: Node.js 18+ or 20+ LTS recommended for building the frontend.
- **PostgreSQL**: Accessible PostgreSQL instance with an initialized database and user credentials.
- **Model Weights**: A valid YOLO weights file at `backend/models/yolov8n.pt`.
- **System Video Access**: Network routing to RTSP endpoints, or a local webcam on device index `0` for USB mode.

### Backend Setup

Clone the repository and enter the project directory:

```bash
git clone https://github.com/eslam-adel25/AeroGuard-AI.git
cd AeroGuard-AI
```

#### On Linux / macOS

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

#### On Windows (PowerShell)

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Create `backend/.env` containing your database credentials and secret key:

```dotenv
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/aeroguard
SECRET_KEY=replace-with-a-secure-random-secret-key
```

Start the backend application with Uvicorn:

```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The API will be available at `http://127.0.0.1:8000`, with interactive docs at `/docs` and `/redoc`.

### Frontend Setup

In a separate terminal, navigate to the `frontend` directory, install dependencies, and start the development server:

```bash
cd frontend
npm ci
npm run dev
```

The frontend will run at `http://localhost:5173` and proxy requests to `http://127.0.0.1:8000`.

### Running Together

When both services are running, the application exposes the following endpoints:

| Component | Target URL |
| :--- | :--- |
| **Frontend Dashboard** | `http://localhost:5173` |
| **Backend REST API** | `http://127.0.0.1:8000/api/v1` |
| **Interactive OpenAPI Documentation** | `http://127.0.0.1:8000/docs` |
| **ReDoc Technical Specification** | `http://127.0.0.1:8000/redoc` |
| **Telemetry & Alarm WebSocket** | `ws://127.0.0.1:8000/ws/dashboard?token=<access-token>` |

### Production-Oriented Command Example

To bind the backend service across specific network interfaces behind a reverse proxy (e.g., Nginx):

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

> [!IMPORTANT]
> Because camera workers and stream states are maintained in-process within the singleton `AIProcessor`, running Uvicorn with multiple workers (`--workers > 1`) will partition stream memory across separate processes. In this architecture, run a single backend worker process per host.
> 
> Build the frontend for production using `npm run build` and serve the compiled assets in `frontend/dist/` via a production web server.

---

## Dependencies and Scripts

### Technology Stack

| Architecture Layer | Core Technologies and Packages |
| :--- | :--- |
| **Frontend Framework** | React, TypeScript, Vite, React Router |
| **Styling & Animation** | Tailwind CSS, Lucide React, Framer Motion |
| **Data Fetching & Visualization** | Axios, Recharts, React Context API |
| **Internationalization** | i18next, react-i18next |
| **Backend HTTP & Routing** | FastAPI, Starlette, Uvicorn |
| **Database & Migrations** | SQLAlchemy, psycopg2-binary, Alembic |
| **Security & Authentication** | python-jose (JWT), passlib / bcrypt, python-dotenv |
| **Inference & Computer Vision** | OpenCV (headless), NumPy, PyTorch, Ultralytics YOLO |
| **Document Compilation** | fpdf2 (PDF), pandas, openpyxl (Excel) |
| **Real-Time Communication** | Native WebSockets |

### Backend Dependencies

Backend requirements are pinned in `backend/requirements.txt`. Note that:

- `pytest` is not included in `requirements.txt`. Install it separately in your virtual environment to run tests.
- Optional tracking adapters (e.g., ByteTrack, DeepSORT) are not part of the default requirements and must be installed manually if desired.

### Frontend Dependencies and Scripts

Available scripts defined in `frontend/package.json`:

| Command | Action Performed |
| :--- | :--- |
| `npm ci` | Clean installation of all dependencies strictly matching `package-lock.json`. |
| `npm run dev` | Starts the Vite development server with hot module replacement and proxying. |
| `npm run build` | Runs TypeScript compilation (`tsc -b`) and bundles production assets. |
| `npm run preview` | Serves the locally compiled production build for preview testing. |
| `npm run lint` | Executes ESLint to validate frontend code style and typing. |

---

## Tests and Quality Checks

### Running Backend Tests

Backend tests are located in `backend/tests/`. To run the full test suite, install `pytest` and execute:

```bash
cd backend
python -m pytest tests
```

#### Key Test Modules

| Test File | Verification Area |
| :--- | :--- |
| `test_multi_camera_runtime.py` | Multi-stream worker isolation, start/stop lifecycle, and concurrent workers. |
| `test_alert_screenshot_persistence.py`| Verification of disk persistence for event screenshots. |
| `test_report_service.py` | Detection metrics aggregation and analytical calculations. |
| `test_camera_ownership.py` | User and administrator authorization checks on camera access. |
| `test_camera_stream_auth.py` | Authentication enforcement on the MJPEG stream endpoint. |
| `test_auth_flow.py`, `test_auth_datetime.py` | Password validation, token generation, and expiration mechanics. |
| `test_person_identity.py` | In-memory session identity registry behavior. |
| `test_rule_line_coordinates.py` | Geometric coordinate normalization for zones and tripwire lines. |
| `test_detection_persistence.py` | Database persistence logic for detections and alert events. |

Run a focused subset of tests:

```bash
python -m pytest tests/test_multi_camera_runtime.py tests/test_alert_screenshot_persistence.py
```

### Running Frontend Checks

```bash
cd frontend
npm run lint
npm run build
```

---

## Troubleshooting

### Backend Fails Before Server Starts

- **Missing Environment File**: Ensure `backend/.env` exists and contains a valid `DATABASE_URL`. The database module raises an exception on import if this is unset.
- **Database Connection Errors**: Verify that PostgreSQL is running and accessible using the connection parameters in `DATABASE_URL`.
- **Missing YOLO Weights**: Verify that `backend/models/yolov8n.pt` exists and is not an empty file. If missing, the server will log an error and start with `ai_engine = None`, causing camera start requests to fail.
- **Python Version Mismatches**: Use Python `3.12.10` as specified in `backend/runtime.txt` to avoid binary wheel issues with PyTorch or OpenCV.

### Vite Cannot Reach API or WebSocket

- Verify that both the backend (`http://127.0.0.1:8000`) and the Vite development server (`http://localhost:5173`) are running simultaneously.
- If running the backend on a custom port, update `VITE_API_PROXY_TARGET` in your frontend environment file.
- Inspect the browser console and network panel for HTTP 401/403 responses or WebSocket handshake rejections. Remember that WebSocket connections require a valid token query parameter.

### RTSP Camera Fails to Start

- Confirm the stream URL begins with `rtsp://` or `rtsps://` and includes necessary credentials (`rtsp://user:pass@host:port/path`).
- Confirm that the RTSP server is reachable from the backend host and produces decodable video frames. A ping response alone does not confirm stream accessibility.
- Check the backend console for OpenCV `VideoCapture` decode or timeout errors.
- Cameras briefly show as `Processing` during initialization. If connection negotiation fails, the worker terminates and transitions to `Offline`.

### Uploaded Video or Local USB Source Unavailable

- Uploaded videos must match permitted formats (`.mp4`, `.mov`, `.avi`, `.mkv`, `.webm`) and remain below the 200 MiB limit.
- Video files are stored on the backend host; they are not streamed from the client browser.
- USB device index `0` refers to hardware connected directly to the backend server. A client machine's local webcam cannot be accessed through the USB option when connecting to a remote backend.

### Alerts, Screenshots, or Analytics Are Missing

- Alert evaluation requires that camera zones, rules, and confidence thresholds are configured and enabled in user settings.
- Bounding box classifications must match labels produced by the loaded YOLO model.
- Not all detections generate persistent `AIEvent` rows, and screenshots are only captured after an alert persists for the required duration.
- Historical analytics aggregate `Detection` rows, whereas live alarms reflect in-memory worker state. These are separate data stores.

### Email Verification Does Not Arrive

- Email verification is disabled unless `REQUIRE_EMAIL_VERIFICATION=true` is set in `backend/.env`.
- When enabled, functional SMTP settings (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`) are required. If missing, verification tokens are written to the backend application logs instead of being sent via email.
- Verify that `FRONTEND_BASE` matches your frontend URL so generated verification links direct users to the correct address.

---

## Security and Limitations

> [!CAUTION]
> Review the following security considerations before deploying AeroGuard AI outside an isolated local development environment.

- **Default JWT Secret Fallback**: If neither `SECRET_KEY` nor `JWT_SECRET` is set, the application falls back to a hardcoded string (`super_secret`). Always generate and configure a strong secret key in production environments.
- **Default Demo Credentials**: The codebase includes a demo credential fallback (`admin123`) in development helpers. Do not deploy demo accounts or credentials to production instances.
- **Unprotected Diagnostic Endpoint**: `GET /api/v1/auth/create-admin` requires no authentication and returns total user counts and usernames. Restrict or remove this endpoint before deploying.
- **Static Directory Mounting**: The `backend/uploads` directory is mounted directly as static content at `/uploads`. Any file stored in this directory can be accessed without passing through the ownership checks enforced by `/api/v1/ai/events/{id}/screenshot`.
- **Public Report PDF Access**: Compiled report PDFs are written to `backend/uploads/reports/`, which falls within the statically mounted upload tree.
- **WebSocket Broadcast Scope**: The WebSocket server enforces ownership filtering on `ai_event` and `alarm_state` messages, but broadcasts `camera_status` and `ai_status` updates to **all** connected clients.
- **Client Token Storage**: Access tokens are stored in browser `localStorage` and passed to WebSockets via URL query parameters. Use TLS (`https://` and `wss://`) to protect tokens in transit, and avoid logging full WebSocket query strings.
- **CORS Configuration**: By default, CORS origins are restricted to `http://localhost:5173` and `http://127.0.0.1:5173`. Update allowed origins when deploying to other domains.
- **Worker Memory Isolation**: Ingestion workers run as background threads within the main backend process. If the process terminates, all active streams stop and in-memory tracking states are cleared.
- **File Upload Limits**: While extension and 200 MiB size checks are enforced, file storage quotas, automated file cleanup, and virus scanning must be configured at the infrastructure level.
- **Authentication Helper Variations**: The backend source also contains separate auth helpers in `security.py` and `auth_middleware.py`. Verify the specific route dependency when assessing access behavior; a router's tag or module name does not prove a uniform permission policy.
- **License**: The repository does not include a root `LICENSE` file. Do not assume licensing permissions based solely on project naming.

---

## Documentation Index

The following supplemental documentation files are located in the `docs/` directory:

| Document | Subject |
| :--- | :--- |
| [Architecture](docs/Architecture.md) | In-depth technical architecture and subsystem interactions |
| [API](docs/API.md) | Extended REST endpoint specifications and request payloads |
| [AI](docs/AI.md) | Computer vision pipeline and model inference mechanics |
| [Auth](docs/Auth.md) | Authentication models, token lifecycles, and RBAC rules |
| [CameraPipeline](docs/CameraPipeline.md) | Video ingestion, frame decoding, and worker thread lifecycle |
| [Database](docs/Database.md) | Database schema documentation and table relationships |
| [Dependencies](docs/Dependencies.md) | Detailed dependency inventory across backend and frontend |
| [EnvVars](docs/EnvVars.md) | Complete environment variable configuration reference |
| [FolderStructure](docs/FolderStructure.md) | Directory hierarchy and file organization guide |
| [Installation](docs/Installation.md) | Extended deployment and environment setup instructions |
| [Reference](docs/Reference.md) | System specifications and operational reference guide |
| [Reports](docs/Reports.md) | Reporting engine, aggregation logic, and export options |
| [Security](docs/Security.md) | Security policies, authentication flows, and known limitations |
| [Settings](docs/Settings.md) | User settings schemas and runtime configuration guide |
| [WebSockets](docs/WebSockets.md) | Real-time communication protocol and message schemas |

> [!NOTE]
> Those documents provide additional detail but may not all be synchronized with the current implementation. Cross-check behavior-dependent instructions against source. No `docs/Localization.md` or `docs/Notifications.md` was present in the inspected documentation directory.

---

## Contributing

To contribute changes to AeroGuard AI:

1. Create a focused topic branch from the main branch.
2. Keep modifications scoped directly to the feature or issue being addressed.
3. Write or update corresponding backend tests in `backend/tests/` and verify that they pass.
4. Run frontend linting (`npm run lint`) and build validation (`npm run build`) for client-side changes.
5. Update relevant technical documentation in `docs/` and review your changes with `git diff --check`.

There is no separate root contribution guide in the files inventoried above. Avoid claiming tests passed unless they were run in the environment being reported.
