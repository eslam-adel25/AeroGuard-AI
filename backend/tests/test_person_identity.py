import numpy as np
from types import SimpleNamespace

from app.ai.identity import PersonIdentityRegistry


def person(track_id, bbox=(10, 10, 40, 70)):
    return SimpleNamespace(track_id=track_id, class_name="person", bbox=list(bbox))


def solid_frame(color):
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    frame[:, :] = color
    return frame


def test_two_people_receive_unique_camera_local_ids():
    registry = PersonIdentityRegistry()
    tracks = [person(1, (5, 5, 35, 75)), person(2, (55, 5, 85, 75))]
    frame = solid_frame((40, 80, 160))

    assignments = registry.assign(tracks, frame, now=1)

    assert assignments == {1: 1, 2: 2}


def test_track_loss_and_return_recovers_identity_from_appearance():
    registry = PersonIdentityRegistry()
    frame = solid_frame((40, 80, 160))

    first = registry.assign([person(1)], frame, now=1)
    registry.assign([], frame, now=2)
    returned = registry.assign([person(9)], frame, now=3)

    assert first == {1: 1}
    assert returned == {9: 1}


def test_unmatched_person_gets_new_reserved_id():
    registry = PersonIdentityRegistry()
    first_frame = solid_frame((40, 80, 160))
    different_frame = solid_frame((160, 40, 80))

    registry.assign([person(1)], first_frame, now=1)
    registry.assign([], first_frame, now=2)
    new_person = registry.assign([person(3)], different_frame, now=3)

    assert new_person == {3: 2}


def test_expired_identity_is_not_reused():
    registry = PersonIdentityRegistry(retention_seconds=5)
    frame = solid_frame((40, 80, 160))

    registry.assign([person(1)], frame, now=1)
    registry.assign([], frame, now=2)
    new_person = registry.assign([person(3)], solid_frame((160, 40, 80)), now=7.1)

    assert new_person == {3: 2}
    assert 1 not in registry.identities
    assert registry._next_person_id == 3


def test_separate_registries_keep_camera_ids_isolated():
    frame = solid_frame((40, 80, 160))
    camera_a = PersonIdentityRegistry()
    camera_b = PersonIdentityRegistry()

    assert camera_a.assign([person(1)], frame, now=1) == {1: 1}
    assert camera_b.assign([person(1)], frame, now=1) == {1: 1}
