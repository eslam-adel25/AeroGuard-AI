import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

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


def test_bag_owner_is_preserved_after_separation():
    processor = AIProcessor.__new__(AIProcessor)
    processor.bag_owner_state = {}
    processor.display_id_state = {}

    person = SimpleNamespace(track_id=14, bbox=[10, 10, 50, 120], class_name="person")
    bag = SimpleNamespace(track_id=88, bbox=[20, 90, 60, 140], class_name="bag")

    owner_map = processor._assign_bag_owner("cam-1", [person], [bag])
    assert owner_map[88] == 14

    owner_map = processor._assign_bag_owner("cam-1", [], [bag])
    assert owner_map[88] == 14
