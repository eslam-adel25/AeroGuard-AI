import logging
from typing import Callable, List, Optional

from fastapi import WebSocket
from ..core.tenant import PLATFORM_TENANT_SCOPE

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[tuple[WebSocket, Optional[str], Optional[str]]] = []
        self.authorization_checks: dict[WebSocket, Callable[[], bool]] = {}
        self.feature_authorization_checks: dict[
            WebSocket, Callable[[str], bool]
        ] = {}
        self.connection_tenants: dict[WebSocket, Optional[str]] = {}

    async def connect(
        self,
        websocket: WebSocket,
        user_id: Optional[str] = None,
        role: Optional[str] = None,
        authorization_check: Optional[Callable[[], bool]] = None,
        feature_authorization_check: Optional[Callable[[str], bool]] = None,
        customer_profile_id: Optional[str] = None,
    ):
        await websocket.accept()
        self.active_connections.append((websocket, user_id, role))
        self.connection_tenants[websocket] = customer_profile_id
        if authorization_check:
            self.authorization_checks[websocket] = authorization_check
        if feature_authorization_check:
            self.feature_authorization_checks[websocket] = (
                feature_authorization_check
            )

    def disconnect(self, websocket: WebSocket):
        self.authorization_checks.pop(websocket, None)
        self.feature_authorization_checks.pop(websocket, None)
        self.connection_tenants.pop(websocket, None)
        self.active_connections = [
            connection
            for connection in self.active_connections
            if connection[0] is not websocket
        ]

    async def broadcast(
        self,
        message: dict,
        audience_user_id: Optional[str] = None,
        audience_customer_profile_id: Optional[str] = None,
    ):
        dead_connections = []
        for connection, user_id, _role in self.active_connections:
            authorization_check = self.authorization_checks.get(connection)
            if authorization_check:
                try:
                    authorized = authorization_check()
                except Exception:
                    logger.exception("WebSocket account authorization check failed")
                    authorized = False
                if not authorized:
                    dead_connections.append(connection)
                    continue
            if audience_customer_profile_id is not None:
                if (
                    self.connection_tenants.get(connection)
                    != audience_customer_profile_id
                    and self.connection_tenants.get(connection)
                    != PLATFORM_TENANT_SCOPE
                ):
                    continue
            elif (
                message.get("event")
                in {
                    "ai_event",
                    "alarm_state",
                    "tripwire_alarm_state",
                    "tripwire_alarm_snapshot",
                    "camera_status",
                    "tripwire_state",
                    "ai_status",
                }
                and (
                    audience_user_id is None
                    or user_id != audience_user_id
                )
            ):
                continue
            required_feature = {
                "camera_status": "cameras",
                "tripwire_state": "cameras",
                "ai_status": "cameras",
                "ai_event": "alerts",
                "alarm_state": "alerts",
                "tripwire_alarm_state": "alerts",
                "tripwire_alarm_snapshot": "alerts",
                "alarm_state_snapshot": "alerts",
            }.get(message.get("event"))
            feature_check = self.feature_authorization_checks.get(connection)
            if required_feature and feature_check:
                try:
                    feature_authorized = feature_check(required_feature)
                except Exception:
                    logger.exception(
                        "WebSocket feature authorization check failed"
                    )
                    feature_authorized = False
                if not feature_authorized:
                    continue
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.append(connection)
        for connection in dead_connections:
            self.disconnect(connection)


manager = ConnectionManager()