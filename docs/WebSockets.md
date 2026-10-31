# WebSocket Architecture

The backend exposes a dashboard WebSocket endpoint that the frontend uses for live AI and camera updates.

- Endpoint: ws://<host>/ws/dashboard?token=<ACCESS_TOKEN>
- The server validates the JWT passed in the token query parameter before accepting the socket.
- The frontend opens this endpoint from frontend/src/services/socket.ts.
- Admin and Officer connections require active customer membership and an
  enabled dashboard, cameras, or alerts feature. Owner connections are
  authenticated against the database-backed Owner role and receive
  platform-wide messages.

Connection manager

- backend/app/websocket/manager.py maintains the active socket set.
- It accepts new connections, removes closed ones, and broadcasts JSON messages
  only to authorized recipients.

Message types

- new_alert — high-priority alert metadata.
- ai_status — periodic engine metrics such as FPS and object counts.
- ai_event — detailed AI event payloads.
- alarm_state — alarm state changes for a specific camera.
- camera_status — camera online/offline updates.
- tripwire_state — live occupancy updates for a specific camera.

Camera status, metrics, and tripwire messages are delivered only to the
camera's CustomerProfile audience and require the cameras feature for customer
users. AI events and alarm-state messages require the alerts feature and use
the same customer audience. Owner receives platform-wide broadcasts.

Security and scaling notes

- The current implementation authenticates the WebSocket with a token in the query string.
- Customer identity and feature permissions are resolved from the authenticated
  database user; clients cannot choose a tenant audience.
- The connection manager is in-memory and is suitable for single-instance deployments; a shared pub/sub layer would be required for multi-instance scaling.
