import os
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ai.processor import AIProcessor


class FakeTensor:
    def __init__(self, value):
        self.value = value

    def cpu(self):
        return self

    def numpy(self):
        return np.asarray(self.value)


class FakeBoxes:
    def __init__(self, boxes, class_ids, confidences):
        self.xyxy = FakeTensor(boxes)
        self.cls = FakeTensor(class_ids)
        self.conf = FakeTensor(confidences)

    def __len__(self):
        return len(self.conf.value)


def make_result(boxes, class_ids, confidences):
    return [
        SimpleNamespace(
            boxes=FakeBoxes(boxes, class_ids, confidences),
        )
    ]


def test_specialist_class_map_uses_loaded_model_names():
    assert AIProcessor._build_fire_smoke_class_map(
        {0: "smoke", 1: "fire", 2: "person"}
    ) == {0: "smoke", 1: "fire"}


def test_specialist_detections_preserve_class_bbox_and_confidence():
    detections = AIProcessor._extract_model_detections(
        make_result([[10.2, 20.8, 100.9, 120.1]], [1], [0.87]),
        {0: "smoke", 1: "fire"},
        {"fire", "smoke"},
        {0: "smoke", 1: "fire"},
    )

    assert detections == [
        {
            "bbox": [10, 20, 100, 120],
            "class_name": "fire",
            "confidence": 0.87,
        }
    ]


def test_overlapping_same_class_detections_are_deduplicated():
    detections = AIProcessor._merge_detections(
        [
            {"bbox": [0, 0, 100, 100], "class_name": "fire", "confidence": 0.7},
            {"bbox": [5, 5, 95, 95], "class_name": "fire", "confidence": 0.9},
            {"bbox": [5, 5, 95, 95], "class_name": "smoke", "confidence": 0.8},
        ]
    )

    assert detections == [
        {"bbox": [5, 5, 95, 95], "class_name": "fire", "confidence": 0.9},
        {"bbox": [5, 5, 95, 95], "class_name": "smoke", "confidence": 0.8},
    ]


def test_fire_and_smoke_settings_gate_specialist_alerts():
    disabled = SimpleNamespace(
        fire_detection_enabled=False,
        smoke_detection_enabled=False,
    )
    enabled = SimpleNamespace(
        fire_detection_enabled=True,
        smoke_detection_enabled=True,
    )

    assert not AIProcessor._is_fire_smoke_enabled("fire", disabled)
    assert not AIProcessor._is_fire_smoke_enabled("smoke", disabled)
    assert AIProcessor._is_fire_smoke_enabled("fire", enabled)
    assert AIProcessor._is_fire_smoke_enabled("smoke", enabled)
    assert AIProcessor._is_fire_smoke_enabled("flame", enabled)


def test_specialist_failure_does_not_replace_general_model(monkeypatch):
    processor = AIProcessor.__new__(AIProcessor)
    processor.fire_smoke_model_path = "missing.pt"
    processor.fire_smoke_model = object()
    processor.fire_smoke_class_map = {0: "fire"}
    processor.model = object()

    def fail_to_prepare_model(_path):
        raise FileNotFoundError("specialist weights unavailable")

    monkeypatch.setattr(processor, "_ensure_fire_smoke_model", fail_to_prepare_model)
    general_model = processor.model
    processor._load_fire_smoke_model()

    assert processor.model is general_model
    assert processor.fire_smoke_model is None
    assert processor.fire_smoke_class_map == {}


def test_general_model_path_remains_separate_from_specialist_model():
    general_path = Path(r"D:\GP1\backend\models\yolov8n.pt")
    specialist_path = Path(r"D:\GP1\backend\models\fire-smoke-yolov8n.pt")

    assert general_path.exists()
    assert specialist_path.exists()
    assert general_path != specialist_path
