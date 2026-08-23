import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ai.processor import _build_empty_model_result, _get_source_frame_period


def test_empty_model_result_boxes_is_a_lenable_instance():
    result = _build_empty_model_result()[0]
    boxes = result.boxes

    assert not isinstance(boxes, type)
    assert len(boxes) == 0
    assert boxes.xyxy == []
    assert boxes.cls == []
    assert boxes.conf == []


def test_empty_model_result_produces_no_downstream_detections():
    boxes = _build_empty_model_result()[0].boxes

    detections = [
        (box, cls_idx, confidence)
        for box, cls_idx, confidence in zip(
            boxes.xyxy,
            boxes.cls,
            boxes.conf,
        )
    ]

    assert detections == []


class FakeCapture:
    def __init__(self, fps):
        self.fps = fps

    def get(self, property_id):
        return self.fps


def test_file_source_frame_period_uses_capture_fps():
    assert _get_source_frame_period(FakeCapture(25), True) == 0.04


def test_live_source_is_not_file_paced():
    assert _get_source_frame_period(FakeCapture(25), False) is None


def test_invalid_file_fps_does_not_create_arbitrary_pacing():
    assert _get_source_frame_period(FakeCapture(0), True) is None