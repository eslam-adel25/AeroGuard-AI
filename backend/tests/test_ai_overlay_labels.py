import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import app.ai.processor as processor_module
from app.ai.processor import AIProcessor


def test_overlay_label_includes_track_id_and_class_name():
    assert AIProcessor._format_overlay_label(7, "person") == "ID:007 Person"


def test_overlay_label_formats_non_person_objects():
    assert AIProcessor._format_overlay_label(17, "car") == "ID:017 Car"


def test_display_ids_are_sequential_for_visible_objects():
    processor = AIProcessor.__new__(AIProcessor)
    processor.display_id_state = {}

    first = SimpleNamespace(track_id=37, bbox=[10, 10, 40, 60], class_name="person")
    second = SimpleNamespace(track_id=50, bbox=[60, 10, 100, 60], class_name="person")

    assigned = processor._assign_display_ids("cam-1", [first, second])

    assert assigned == {37: 1, 50: 2}
    assert processor.display_id_state["cam-1"][37] == 1
    assert processor.display_id_state["cam-1"][50] == 2


def test_person_fallback_threshold_is_lower_for_recall():
    assert AIProcessor._get_person_confidence_threshold(0.5) == 0.38


def test_bag_owner_requires_multiple_consecutive_frames_to_assign():
    processor = AIProcessor.__new__(AIProcessor)
    processor.bag_owner_state = {}
    processor.display_id_state = {}
    processor.bag_owner_evidence = {}
    processor.bag_owner_status = {}

    person = SimpleNamespace(track_id=14, bbox=[10, 10, 50, 120], class_name="person")
    bag = SimpleNamespace(track_id=88, bbox=[20, 90, 60, 140], class_name="bag")

    first_assignment = processor._assign_bag_owner("cam-1", [person], [bag])
    assert first_assignment.get(88) is None

    second_assignment = processor._assign_bag_owner("cam-1", [person], [bag])
    assert second_assignment.get(88) is None

    third_assignment = processor._assign_bag_owner("cam-1", [person], [bag])
    assert third_assignment[88] == 14


def test_multiple_bags_share_the_owners_persistent_person_id():
    processor = AIProcessor.__new__(AIProcessor)
    processor.bag_owner_state = {}
    processor.bag_owner_person_state = {}
    processor.bag_owner_evidence = {}
    processor.bag_owner_status = {}

    person = SimpleNamespace(track_id=14, bbox=[10, 10, 50, 120], class_name="person")
    first_bag = SimpleNamespace(track_id=88, bbox=[20, 90, 60, 140], class_name="bag")
    second_bag = SimpleNamespace(track_id=89, bbox=[60, 90, 100, 140], class_name="bag")

    for _ in range(3):
        owner_map = processor._assign_bag_owner(
            "cam-1",
            [person],
            [first_bag, second_bag],
            {14: 6},
        )

    assert owner_map == {88: 14, 89: 14}
    assert processor.bag_owner_person_state["cam-1"] == {88: 6, 89: 6}


def test_bag_persistent_owner_id_survives_owner_track_loss():
    processor = AIProcessor.__new__(AIProcessor)
    processor.bag_owner_state = {}
    processor.bag_owner_person_state = {}
    processor.bag_owner_evidence = {}
    processor.bag_owner_status = {}

    person = SimpleNamespace(track_id=14, bbox=[10, 10, 50, 120], class_name="person")
    bag = SimpleNamespace(track_id=88, bbox=[20, 90, 60, 140], class_name="bag")

    for _ in range(3):
        processor._assign_bag_owner("cam-1", [person], [bag], {14: 6})
    for _ in range(3):
        processor._assign_bag_owner("cam-1", [], [bag], {})

    assert processor.bag_owner_person_state["cam-1"][88] == 6
    assert processor.bag_owner_status["cam-1"][88] == "temporary_unattended"


def test_bag_owner_is_lost_after_consecutive_missing_frames():
    processor = AIProcessor.__new__(AIProcessor)
    processor.bag_owner_state = {}
    processor.display_id_state = {}
    processor.bag_owner_evidence = {}
    processor.bag_owner_status = {}

    person = SimpleNamespace(track_id=14, bbox=[10, 10, 50, 120], class_name="person")
    bag = SimpleNamespace(track_id=88, bbox=[20, 90, 60, 140], class_name="bag")

    processor._assign_bag_owner("cam-1", [person], [bag])
    processor._assign_bag_owner("cam-1", [person], [bag])
    processor._assign_bag_owner("cam-1", [person], [bag])

    lost_assignment = processor._assign_bag_owner("cam-1", [], [bag])
    assert lost_assignment.get(88) == 14

    lost_assignment = processor._assign_bag_owner("cam-1", [], [bag])
    assert lost_assignment.get(88) == 14

    lost_assignment = processor._assign_bag_owner("cam-1", [], [bag])
    assert lost_assignment.get(88) is None


def test_bag_owner_enters_temporary_and_unattended_states():
    processor = AIProcessor.__new__(AIProcessor)
    processor.bag_owner_state = {}
    processor.display_id_state = {}
    processor.bag_owner_evidence = {}
    processor.bag_owner_status = {}

    person = SimpleNamespace(track_id=14, bbox=[10, 10, 50, 120], class_name="person")
    bag = SimpleNamespace(track_id=88, bbox=[20, 90, 60, 140], class_name="bag")

    original_timeout = processor_module.UNATTENDED_TIMEOUT_SECONDS
    original_loss_required = processor_module.OWNERSHIP_LOSS_REQUIRED_FRAMES
    processor_module.UNATTENDED_TIMEOUT_SECONDS = 0
    processor_module.OWNERSHIP_LOSS_REQUIRED_FRAMES = 1
    try:
        processor._assign_bag_owner("cam-1", [person], [bag])
        processor._assign_bag_owner("cam-1", [person], [bag])
        processor._assign_bag_owner("cam-1", [person], [bag])

        temporary_assignment = processor._assign_bag_owner("cam-1", [], [bag])
        assert temporary_assignment.get(88) is None
        assert processor.bag_owner_status["cam-1"][88] == "temporary_unattended"

        unattended_assignment = processor._assign_bag_owner("cam-1", [], [bag])
        assert unattended_assignment.get(88) is None
        assert processor.bag_owner_status["cam-1"][88] == "unattended"
    finally:
        processor_module.UNATTENDED_TIMEOUT_SECONDS = original_timeout
        processor_module.OWNERSHIP_LOSS_REQUIRED_FRAMES = original_loss_required
