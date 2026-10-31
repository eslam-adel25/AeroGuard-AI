import asyncio

from app.websocket.manager import ConnectionManager


class FakeWebSocket:
    def __init__(self):
        self.messages = []
        self.accepted = False

    async def accept(self):
        self.accepted = True

    async def send_json(self, message):
        self.messages.append(message)


def test_revoked_customer_is_removed_before_next_broadcast():
    manager = ConnectionManager()
    websocket = FakeWebSocket()
    authorization = {"allowed": True}

    async def run():
        await manager.connect(
            websocket,
            user_id="customer-1",
            role="Officer",
            authorization_check=lambda: authorization["allowed"],
        )
        await manager.broadcast(
            {"event": "camera_status"},
            audience_user_id="customer-1",
        )
        authorization["allowed"] = False
        await manager.broadcast(
            {"event": "camera_status"},
            audience_user_id="customer-1",
        )

    asyncio.run(run())

    assert websocket.accepted is True
    assert websocket.messages == [{"event": "camera_status"}]
    assert manager.active_connections == []
    assert websocket not in manager.authorization_checks


def test_websocket_broadcast_respects_current_feature_permission():
    manager = ConnectionManager()
    websocket = FakeWebSocket()
    feature_access = {"cameras": True, "alerts": False}

    async def run():
        await manager.connect(
            websocket,
            user_id="customer-1",
            role="Officer",
            feature_authorization_check=lambda key: feature_access.get(
                key, False
            ),
        )
        await manager.broadcast(
            {"event": "camera_status"},
            audience_user_id="customer-1",
        )
        await manager.broadcast(
            {"event": "ai_event"},
            audience_user_id="customer-1",
        )

    asyncio.run(run())

    assert websocket.messages == [{"event": "camera_status"}]
    assert websocket in manager.active_connections[0]


def test_camera_websocket_broadcast_is_scoped_to_its_customer():
    manager = ConnectionManager()
    customer_socket = FakeWebSocket()
    other_socket = FakeWebSocket()

    async def run():
        await manager.connect(
            customer_socket,
            user_id="camera-owner",
            role="Officer",
        )
        await manager.connect(
            other_socket,
            user_id="other-customer",
            role="Officer",
        )
        await manager.broadcast(
            {
                "event": "camera_status",
                "data": {"camera_id": "camera-1", "status": "Running"},
            },
            audience_user_id="camera-owner",
        )

    asyncio.run(run())

    assert len(customer_socket.messages) == 1
    assert other_socket.messages == []


def test_admin_websocket_does_not_bypass_customer_audience_scope():
    manager = ConnectionManager()
    admin_socket = FakeWebSocket()

    async def run():
        await manager.connect(
            admin_socket,
            user_id="admin-user",
            role="Admin",
        )
        await manager.broadcast(
            {"event": "ai_event", "data": {"event_id": "foreign-event"}},
            audience_user_id="other-customer",
        )
        await manager.broadcast(
            {"event": "ai_event", "data": {"event_id": "unscoped-event"}},
        )

    asyncio.run(run())

    assert admin_socket.messages == []
