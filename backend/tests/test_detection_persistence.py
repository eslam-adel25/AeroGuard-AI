import os

os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost/db")

from app.ai.processor import AIProcessor, build_detection_record


def test_build_detection_record_for_standard_detection() -> None:
    detection = build_detection_record(
        camera_id="11111111-1111-1111-1111-111111111111",
        owner_id="22222222-2222-2222-2222-222222222222",
        detection_type="PERSON",
        confidence=0.91,
        status=None,
    )

    assert detection.detection_type == "PERSON"
    assert detection.confidence == 0.91
    assert detection.priority == "Medium"
    assert detection.is_violation is False
    assert detection.violation_type is None


def test_build_detection_record_for_alert_detection() -> None:
    detection = build_detection_record(
        camera_id="11111111-1111-1111-1111-111111111111",
        owner_id="22222222-2222-2222-2222-222222222222",
        detection_type="FIRE",
        confidence=0.99,
        status="DANGER",
    )

    assert detection.priority == "Critical"
    assert detection.is_violation is True
    assert detection.violation_type == "DANGER"


def test_build_detection_record_for_smoke_alert() -> None:
    detection = build_detection_record(
        camera_id="11111111-1111-1111-1111-111111111111",
        owner_id="22222222-2222-2222-2222-222222222222",
        detection_type="SMOKE",
        confidence=0.88,
        status="DANGER",
    )

    assert detection.detection_type == "SMOKE"
    assert detection.priority == "Critical"
    assert detection.is_violation is True
    assert detection.violation_type == "DANGER"


def test_build_detection_record_preserves_non_fire_labels() -> None:
    detection = build_detection_record(
        camera_id="11111111-1111-1111-1111-111111111111",
        owner_id="22222222-2222-2222-2222-222222222222",
        detection_type="Baggage",
        confidence=0.75,
        status=None,
    )

    assert detection.detection_type == "Baggage"
    assert detection.priority == "Medium"
    assert detection.is_violation is False


def test_persist_detection_uses_camera_owner_uuid_when_present() -> None:
    processor = AIProcessor.__new__(AIProcessor)
    processor._detection_persist_cooldown = {}

    class FakeRepo:
        def __init__(self, db_session):
            self.db_session = db_session

        def save_detection(self, detection):
            assert detection.owner_id == "22222222-2222-2222-2222-222222222222"
            return detection

    class FakeSession:
        pass

    processor._persist_detection = AIProcessor._persist_detection.__get__(processor, AIProcessor)
    processor._persist_detection.__globals__['DetectionRepository'] = FakeRepo

    result = processor._persist_detection(
        FakeSession(),
        "11111111-1111-1111-1111-111111111111",
        "22222222-2222-2222-2222-222222222222",
        "PERSON",
        0.91,
        7,
        None,
    )

    assert result is not None
    assert result.owner_id == "22222222-2222-2222-2222-222222222222"
