from typing import List, Optional
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[tuple[WebSocket, Optional[str], Optional[str]]] = []

    async def connect(
        self,
        websocket: WebSocket,
        user_id: Optional[str] = None,
        role: Optional[str] = None,
    ):
        await websocket.accept()
        self.active_connections.append((websocket, user_id, role))

    def disconnect(self, websocket: WebSocket):
        self.active_connections = [
            connection
            for connection in self.active_connections
            if connection[0] is not websocket
        ]

    async def broadcast(self, message: dict, audience_user_id: Optional[str] = None):
        dead_connections = []
        for connection, user_id, role in self.active_connections:
            if (
                message.get("event") in {"ai_event", "alarm_state"}
                and role != "Administrator"
                and (
                    audience_user_id is None
                    or user_id != audience_user_id
                )
            ):
                continue
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.append(connection)
        for connection in dead_connections:
            self.disconnect(connection)


manager = ConnectionManager()