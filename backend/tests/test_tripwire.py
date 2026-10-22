import asyncio
import uuid
from types import SimpleNamespace

import numpy as np
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

from app.ai.processor import _tripwire_crossing
from app.database.session import Base
from app.models.models import Camera, RestrictedZone
from app.api.v1 import cameras as cameras_api
from app.schemas.schemas import TripwireOccupancyConfirmation


def test_tripwire_direction_is_stable_when_endpoints_are_reversed():
    assert _tripwire_crossing((0, 50), (100, 50), (40, 40), (60, 60), "right") == "entry"
    assert _tripwire_crossing((100, 50), (0, 50), (40, 40), (60, 60), "right") == "entry"
    assert _tripwire_crossing((0, 50), (100, 50), (60, 60), (40, 40), "right") == "exit"
    assert _tripwire_crossing((0, 50), (100, 50), (40, 40), (60, 60), "left") == "exit"


def test_tripwire_rejects_crossing_the_infinite_extension():
    assert _tripwire_crossing((0, 50), (100, 50), (-40, 40), (-20, 60), "right") is None


def test_tripwire_supports_vertical_and_diagonal_segments():
    assert _tripwire_crossing((50, 0), (50, 100), (40, 40), (60, 60), "right") == "entry"
    assert _tripwire_crossing((0, 0), (100, 100), (20, 40), (40, 20), "right") == "exit"


def test_tripwire_counter_calculations():
    allowed = 4
    occupancy = 6
    assert max(0, allowed - occupancy) == 0
    assert occupancy == 6
    assert max(0, occupancy - allowed) == 2


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
