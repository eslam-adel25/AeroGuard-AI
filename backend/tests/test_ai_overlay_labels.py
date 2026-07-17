import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ai.processor import AIProcessor


def test_overlay_label_includes_track_id_and_class_name():
    assert AIProcessor._format_overlay_label(7, "person") == "ID:007 Person"


def test_overlay_label_formats_non_person_objects():
    assert AIProcessor._format_overlay_label(17, "car") == "ID:017 Car"
