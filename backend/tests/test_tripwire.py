import asyncio
import uuid
from types import SimpleNamespace

import numpy as np
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

from app.ai.processor import (
    AIProcessor,
    _tripwire_became_over_limit,
    _tripwire_crossing,
    _tripwire_crossing_with_hysteresis,
    _update_tripwire_occupancy,
)
from app.database.session import Base
from app.models.models import Camera, RestrictedZone
from app.api.v1 import cameras as cameras_api
from app.schemas.schemas import TripwireOccupancyConfirmation
from app.websocket.manager import ConnectionManager


def test_tripwire_direction_uses_horizontal_movement_for_supported_line_geometries():
    cases = [
        ((50, 0), (50, 100), (40, 50), (60, 50)),
        ((0, 50), (100, 50), (40, 40), (60, 60)),
        ((20, 20), (80, 80), (40, 60), (60, 40)),
        ((50, 0), (50, 100), (40, 40), (60, 60)),
    ]

    for a, b, previous, current in cases:
        assert _tripwire_crossing(a, b, previous, current, "right") == "entry"
        assert _tripwire_crossing(a, b, current, previous, "right") == "exit"
        assert _tripwire_crossing(a, b, current, previous, "left") == "entry"
        assert _tripwire_crossing(a, b, previous, current, "left") == "exit"


def test_tripwire_direction_is_stable_when_endpoints_are_reversed():
    previous = (40, 40)
    current = (60, 60)
    assert _tripwire_crossing((0, 50), (100, 50), previous, current, "right") == "entry"
    assert _tripwire_crossing((100, 50), (0, 50), previous, current, "right") == "entry"
    assert _tripwire_crossing((0, 50), (100, 50), current, previous, "right") == "exit"
    assert _tripwire_crossing((100, 50), (0, 50), current, previous, "right") == "exit"
    assert _tripwire_crossing((0, 50), (100, 50), previous, current, "left") == "exit"
    assert _tripwire_crossing((100, 50), (0, 50), previous, current, "left") == "exit"


def test_tripwire_rejects_crossing_the_infinite_extension():
    assert _tripwire_crossing((0, 50), (100, 50), (-40, 40), (-20, 60), "right") is None


def test_tripwire_supports_vertical_and_diagonal_segments():
    assert _tripwire_crossing((50, 0), (50, 100), (40, 40), (60, 60), "right") == "entry"
    assert _tripwire_crossing((0, 0), (100, 100), (20, 40), (40, 20), "right") == "entry"


def test_tripwire_rejects_parallel_motion_and_points_that_do_not_change_sides():
    assert _tripwire_crossing((50, 0), (50, 100), (40, 30), (40, 70), "right") is None
    assert _tripwire_crossing((20, 20), (80, 80), (20, 40), (30, 50), "right") is None
    assert _tripwire_crossing((0, 50), (100, 50), (20, 40), (40, 40), "right") is None


def test_tripwire_rejects_vertical_movement_without_left_or_right_direction():
    assert _tripwire_crossing((0, 50), (100, 50), (50, 40), (50, 60), "right") is None


def test_tripwire_does_not_count_repeated_positions_or_same_side_jitter():
    line = ((50, 0), (50, 100))
    assert _tripwire_crossing(*line, (40, 50), (40, 50), "right") is None
    assert _tripwire_crossing(*line, (40, 50), (41, 51), "right") is None


def test_tripwire_hysteresis_suppresses_boundary_jitter_and_allows_a_later_exit():
    line = ((50, 0), (50, 100))
    track_state = {}

    assert _tripwire_crossing_with_hysteresis(
        *line,
        (40, 50),
        "right",
        track_state,
    ) is None
    assert _tripwire_crossing_with_hysteresis(
        *line,
        (52, 50),
        "right",
        track_state,
    ) is None
    assert _tripwire_crossing_with_hysteresis(
        *line,
        (48, 50),
        "right",
        track_state,
    ) is None
    assert _tripwire_crossing_with_hysteresis(
        *line,
        (54, 50),
        "right",
        track_state,
    ) == "entry"
    assert _tripwire_crossing_with_hysteresis(
        *line,
        (52, 50),
        "right",
        track_state,
    ) is None
    assert _tripwire_crossing_with_hysteresis(
        *line,
        (48, 50),
        "right",
        track_state,
    ) is None
    assert _tripwire_crossing_with_hysteresis(
        *line,
        (46, 50),
        "right",
        track_state,
    ) == "exit"


def test_tripwire_counter_calculations():
    assert _update_tripwire_occupancy(4, "entry") == 5
    assert _update_tripwire_occupancy(4, "exit") == 3
    assert _update_tripwire_occupancy(0, "exit") == 0
    assert _tripwire_became_over_limit("entry", 4, 5, 4)
    assert not _tripwire_became_over_limit("entry", 3, 4, 4)
    assert _tripwire_became_over_limit("entry", 5, 6, 4)
    assert _tripwire_became_over_limit("entry", 6, 7, 4)
    assert not _tripwire_became_over_limit("exit", 5, 4, 4)
    assert not _tripwire_became_over_limit(None, 5, 6, 4)


def test_tripwire_immediate_alert_contains_wire_and_occupancy_metadata(monkeypatch):
    class FakeService:
        def __init__(self):
            self.calls = []

        def register_event(self, **kwargs):
            self.calls.append(kwargs)
            return SimpleNamespace(event_id=uuid.uuid4(), screenshot_path="saved.jpg")

    service = FakeService()
    from app.ai.processor import AIProcessor

    processor = AIProcessor.__new__(AIProcessor)
    monkeypatch.setattr(
        "app.ai.processor.cv2.imencode",
        lambda *_args: (True, SimpleNamespace(tobytes=lambda: b"jpeg")),
    )

    asyncio.run(
        processor._register_immediate_tripwire_alert(
            service,
            "camera-a",
            "wire-a",
            0.9,
            "track-1",
            "owner-a",
            5,
            4,
            1,
            np.zeros((2, 2, 3), dtype=np.uint8),
        )
    )

    assert service.calls[0]["detection_type"] == "TRIPWIRE_OVER_LIMIT"
    assert service.calls[0]["screenshot_bytes"] == b"jpeg"
    assert service.calls[0]["metadata"] == {
        "zone_id": "wire-a",
        "event_kind": "tripwire_over_limit",
        "occupancy": 5,
        "allowed_group_size": 4,
        "over_limit_count": 1,
    }


def test_tripwire_alarm_state_broadcast_is_scoped_to_camera_owner():
    class FakeWebSocket:
        def __init__(self):
            self.messages = []

        async def send_json(self, message):
            self.messages.append(message)

    owner_socket = FakeWebSocket()
    other_socket = FakeWebSocket()
    admin_socket = FakeWebSocket()
    manager = ConnectionManager()
    manager.active_connections = [
        (owner_socket, "owner-a", "User"),
        (other_socket, "owner-b", "User"),
        (admin_socket, "admin", "Administrator"),
    ]

    asyncio.run(
        manager.broadcast(
            {
                "event": "tripwire_alarm_state",
                "data": {
                    "camera_id": "camera-a",
                    "zone_id": "wire-a",
                    "active": True,
                    "event_id": "event-a",
                },
            },
            audience_user_id="owner-a",
        )
    )

    assert len(owner_socket.messages) == 1
    assert other_socket.messages == []
    assert len(admin_socket.messages) == 1


def test_tripwire_alarm_cleanup_is_scoped_to_camera_and_zone():
    processor = AIProcessor.__new__(AIProcessor)
    processor.tripwire_runtime = {
        "camera-a:wire-a": {"occupancy": 5},
        "camera-b:wire-b": {"occupancy": 6},
    }
    processor._active_tripwire_alarm_states = {
        "camera-a": {"wire-a": {"active": True, "event_id": "event-a"}},
        "camera-b": {"wire-b": {"active": True, "event_id": "event-b"}},
    }
    processor._deleted_tripwire_zones = set()

    cleared = processor.clear_tripwire_alarm_state("camera-a", "wire-a")

    assert cleared == {"active": True, "event_id": "event-a"}
    assert "camera-a:wire-a" not in processor.tripwire_runtime
    assert processor.tripwire_runtime["camera-b:wire-b"]["occupancy"] == 6
    assert "camera-a" not in processor._active_tripwire_alarm_states
    assert processor._active_tripwire_alarm_states["camera-b"]["wire-b"][
        "event_id"
    ] == "event-b"
    assert processor._deleted_tripwire_zones == {("camera-a", "wire-a")}


def test_tripwire_zone_deletion_clears_runtime_alarm_and_broadcasts(monkeypatch):
    camera = SimpleNamespace(owner_id="owner-a")
    zone = SimpleNamespace(zone_type="Tripwire")
    cleared = []
    messages = []

    class FakeQuery:
        def __init__(self, model):
            self.model = model

        def filter(self, *_args):
            return self

        def first(self):
            return camera if self.model is Camera else zone

    class FakeDB:
        def query(self, model):
            return FakeQuery(model)

        def delete(self, item):
            assert item is zone

        def commit(self):
            pass

    async def fake_broadcast(message, audience_user_id=None):
        messages.append((message, audience_user_id))

    monkeypatch.setattr(
        cameras_api,
        "ai_engine",
        SimpleNamespace(
            clear_tripwire_alarm_state=lambda camera_id, zone_id: (
                cleared.append((camera_id, zone_id))
                or {"event_id": "event-a"}
            )
        ),
    )
    monkeypatch.setattr(cameras_api.manager, "broadcast", fake_broadcast)

    response = asyncio.run(
        cameras_api.delete_restricted_zone(
            "camera-a",
            "wire-a",
            db=FakeDB(),
            current_user={"user_id": "owner-a", "role": "User"},
        )
    )

    assert response == {"message": "Zone deleted successfully"}
    assert cleared == [("camera-a", "wire-a")]
    assert messages[0][0] == {
        "event": "tripwire_alarm_state",
        "data": {
            "camera_id": "camera-a",
            "zone_id": "wire-a",
            "active": False,
            "event_id": "event-a",
        },
    }
    assert messages[0][1] == "owner-a"


def _build_tripwire_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def test_case_insensitive_startup_predicate_marks_only_tripwires():
    db = _build_tripwire_session()
    try:
        camera_id = uuid.uuid4()
        zones = [
            RestrictedZone(
                zone_id=uuid.uuid4(),
                camera_id=camera_id,
                zone_name=value,
                zone_type=value,
                polygon_coords={"points": [[0, 0], [1, 1]]},
                owner_id=uuid.uuid4(),
                tripwire_requires_confirmation=False,
            )
            for value in ("Tripwire", "tripwire", "TRIPWIRE", "TrIpWiRe")
        ]
        zones.append(
            RestrictedZone(
                zone_id=uuid.uuid4(),
                camera_id=camera_id,
                zone_name="Restricted",
                zone_type="Restricted Area",
                polygon_coords={"points": [[0, 0], [1, 1]]},
                owner_id=uuid.uuid4(),
                tripwire_requires_confirmation=False,
            )
        )
        db.add_all(zones)
        db.commit()

        db.query(RestrictedZone).filter(
            func.lower(RestrictedZone.zone_type) == "tripwire"
        ).update(
            {RestrictedZone.tripwire_requires_confirmation: True},
            synchronize_session=False,
        )
        db.commit()

        refreshed = db.query(RestrictedZone).all()
        assert all(
            zone.tripwire_requires_confirmation
            for zone in refreshed
            if zone.zone_type.lower() == "tripwire"
        )
        assert not next(
            zone.tripwire_requires_confirmation
            for zone in refreshed
            if zone.zone_type == "Restricted Area"
        )
    finally:
        db.close()


def test_confirmation_finds_case_insensitive_tripwire_and_scopes_camera(monkeypatch):
    db = _build_tripwire_session()
    try:
        owner_id = uuid.uuid4()
        camera_id = uuid.uuid4()
        other_camera_id = uuid.uuid4()
        zone = RestrictedZone(
            zone_id=uuid.uuid4(),
            camera_id=camera_id,
            zone_name="Entry",
            zone_type="tRiPwIrE",
            polygon_coords={"points": [[0, 0], [1, 1]]},
            owner_id=owner_id,
            tripwire_current_occupancy=1,
            tripwire_requires_confirmation=True,
        )
        db.add_all(
            [
                Camera(
                    camera_id=camera_id,
                    camera_name="Camera A",
                    location="A",
                    stream_url="rtsp://a",
                    owner_id=owner_id,
                ),
                Camera(
                    camera_id=other_camera_id,
                    camera_name="Camera B",
                    location="B",
                    stream_url="rtsp://b",
                    owner_id=owner_id,
                ),
                zone,
            ]
        )
        db.commit()
        monkeypatch.setattr(cameras_api, "_get_camera_for_user", lambda *_args: True)

        response = cameras_api.confirm_tripwire_occupancy(
            str(camera_id),
            str(zone.zone_id),
            TripwireOccupancyConfirmation(current_occupancy=3),
            db,
            {"user_id": str(owner_id)},
        )
        assert response["zone_name"] == "Entry"
        assert response["tripwire_current_occupancy"] == 3
        assert response["tripwire_requires_confirmation"] is False

        non_tripwire = RestrictedZone(
            zone_id=uuid.uuid4(),
            camera_id=camera_id,
            zone_name="Restricted",
            zone_type="Restricted Area",
            polygon_coords={"points": [[0, 0], [1, 1]]},
            owner_id=owner_id,
        )
        db.add(non_tripwire)
        db.commit()
        for candidate_zone_id, candidate_camera_id in (
            (non_tripwire.zone_id, camera_id),
            (uuid.uuid4(), camera_id),
            (zone.zone_id, other_camera_id),
        ):
            try:
                cameras_api.confirm_tripwire_occupancy(
                    str(candidate_camera_id),
                    str(candidate_zone_id),
                    TripwireOccupancyConfirmation(current_occupancy=4),
                    db,
                    {"user_id": str(owner_id)},
                )
            except Exception as error:
                assert getattr(error, "status_code", None) == 404
            else:
                raise AssertionError("invalid confirmation target must return 404")
    finally:
        db.close()
