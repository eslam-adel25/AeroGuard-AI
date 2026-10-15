import os
import uuid
from datetime import datetime

import pytest
from fastapi import HTTPException

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.v1.ai import (
    get_ai_event,
    list_ai_events,
    mark_ai_event_read,
    mark_all_ai_events_read,
)
from app.models.models import AIEvent, Base, Camera
from app.repositories.ai_repository import AIRepository


@pytest.fixture
def event_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        camera_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        db.add(
            Camera(
                camera_id=camera_id,
                camera_name="Test Camera",
                location="Test Location",
                stream_url="rtsp://example.com/stream",
                owner_id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
            )
        )
        pending = AIEvent(
            event_id=uuid.UUID("aaaaaaaa-0000-4000-8000-000000000001"),
            camera_id=camera_id,
            detection_type="SHORT ALERT",
            severity="High",
            event_metadata={"_pending_screenshot": True},
            created_at=datetime(2026, 1, 1),
        )
        finalized = AIEvent(
            event_id=uuid.UUID("bbbbbbbb-0000-4000-8000-000000000001"),
            camera_id=camera_id,
            detection_type="QUALIFIED ALERT",
            severity="Critical",
            event_metadata={},
            created_at=datetime(2026, 1, 2),
        )
        historical = AIEvent(
            event_id=uuid.UUID("cccccccc-0000-4000-8000-000000000001"),
            camera_id=camera_id,
            detection_type="HISTORICAL ALERT",
            severity="Low",
            event_metadata=None,
            created_at=datetime(2025, 1, 1),
        )
        db.add_all([pending, finalized, historical])
        db.commit()
        yield db, pending, finalized, historical


def test_pending_events_are_hidden_from_search_and_detail(event_db):
    db, pending, finalized, historical = event_db

    suggestions = list_ai_events(
        event_id_prefix=str(pending.event_id)[:8],
        db=db,
        current_user={"role": "Administrator"},
    )
    assert suggestions["items"] == []

    with pytest.raises(HTTPException) as error:
        get_ai_event(
            str(pending.event_id),
            db=db,
            current_user={"role": "Administrator"},
        )
    assert error.value.status_code == 404

    assert get_ai_event(
        str(finalized.event_id),
        db=db,
        current_user={"role": "Administrator"},
    )["event_id"] == str(finalized.event_id)
    assert get_ai_event(
        str(historical.event_id),
        db=db,
        current_user={"role": "Administrator"},
    )["event_id"] == str(historical.event_id)


def test_report_queries_include_only_finalized_and_legacy_events(event_db):
    db, pending, finalized, historical = event_db
    repo = AIRepository(db)

    total, events = repo.query_events_for_report(limit=10)
    event_ids = {event["event_id"] for event in events}

    assert total == 2
    assert event_ids == {str(finalized.event_id), str(historical.event_id)}
    assert str(pending.event_id) not in event_ids
    assert dict(repo.get_event_counts_by_type()) == {
        "QUALIFIED ALERT": 1,
        "HISTORICAL ALERT": 1,
    }


def test_normal_notification_list_hides_pending_and_keeps_legacy_events(event_db):
    db, pending, finalized, historical = event_db
    response = list_ai_events(
        db=db,
        current_user={"role": "Administrator"},
    )
    event_ids = {item["event_id"] for item in response["items"]}

    assert event_ids == {str(finalized.event_id), str(historical.event_id)}
    assert str(pending.event_id) not in event_ids
    assert response["unread_count"] == 2


def test_read_actions_ignore_pending_events(event_db):
    db, pending, finalized, _historical = event_db

    with pytest.raises(HTTPException) as error:
        mark_ai_event_read(
            str(pending.event_id),
            db=db,
            current_user={"role": "Administrator"},
        )
    assert error.value.status_code == 404

    response = mark_all_ai_events_read(
        db=db,
        current_user={"role": "Administrator"},
    )
    assert response["updated"] == 2

    db.refresh(pending)
    db.refresh(finalized)
    assert pending.is_read is False
    assert finalized.is_read is True
