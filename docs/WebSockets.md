# WebSocket Architecture

The backend exposes a single WebSocket endpoint and a connection manager used by the AI engine and services to broadcast live updates.

- Endpoint: `ws://<host>/ws/dashboard?token=<ACCESS_TOKEN>` (see `awro-guard/backend/app/api/v1/websocket_api.py`)
  - The endpoint requires a `token` query parameter (access token - JWT).
  - The server validates the token using `core/security.verify_token`. If invalid, the connection is closed with code `1008`.

- Connection manager: `awro-guard/backend/app/websocket/manager.py`
  - `ConnectionManager.connect(websocket)` accepts and stores the connection.
  - `disconnect(websocket)` removes the connection.
  - `broadcast(message: dict)` sends JSON to all active connections and cleans up dead sockets.

- Producer: `AIService.register_event()` and `AIProcessor` call `manager.broadcast()` and create async tasks to avoid blocking the main loop.

- Message types (frontend expects these shapes in `awro-guard/frontend/src/services/socket.ts`):
  - `new_alert` — high-priority alert metadata
  - `ai_status` — periodic engine metrics (fps, counts)
  - `ai_event` — detailed AI event created and persisted
  - `camera_status` — camera online/offline messages

Security and scaling notes

- WebSocket authentication uses JWT in query string. For additional security consider moving to a short-lived signed cookie or performing an initial authenticated HTTP upgrade handshake.
- The connection manager stores sockets in memory; in a multi-worker or multi-node deployment, use a pub/sub (Redis) to broadcast messages across instances.
