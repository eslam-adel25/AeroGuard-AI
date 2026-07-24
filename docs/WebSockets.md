# WebSocket Architecture

The backend exposes a dashboard WebSocket endpoint that the frontend uses for live AI and camera updates.

- Endpoint: ws://<host>/ws/dashboard?token=<ACCESS_TOKEN>
- The server validates the JWT passed in the token query parameter before accepting the socket.
- The frontend opens this endpoint from frontend/src/services/socket.ts.

Connection manager

- backend/app/websocket/manager.py maintains the active socket set.
- It accepts new connections, removes closed ones, and broadcasts JSON messages to all active clients.

Message types

- new_alert — high-priority alert metadata.
- ai_status — periodic engine metrics such as FPS and object counts.
- ai_event — detailed AI event payloads.
- alarm_state — alarm state changes for a specific camera.
- camera_status — camera online/offline updates.

Security and scaling notes

- The current implementation authenticates the WebSocket with a token in the query string.
- The connection manager is in-memory and is suitable for single-instance deployments; a shared pub/sub layer would be required for multi-instance scaling.
