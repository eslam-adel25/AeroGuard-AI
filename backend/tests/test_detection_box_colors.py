import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ai.processor import AIProcessor


def test_normal_detection_colors_are_non_red():
    assert AIProcessor._get_detection_box_color("person") == (0, 255, 0)
    assert AIProcessor._get_detection_box_color("bag") == (0, 255, 255)
    assert AIProcessor._get_detection_box_color("car") == (255, 0, 0)
    assert AIProcessor._get_detection_box_color("animal") == (0, 165, 255)
    assert AIProcessor._get_detection_box_color("knife") == (255, 0, 255)
    assert AIProcessor._get_detection_box_color("unknown") == (255, 255, 0)
