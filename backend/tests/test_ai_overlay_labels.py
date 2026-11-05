import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import app.ai.processor as processor_module
from app.ai.processor import AIProcessor
from app.ai.tracker import TrackerManager


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


def test_detection_overlay_payload_preserves_original_track_metadata_and_style():
    detections = [
        {
            "track_id": "14",
            "identity_id": 6,
            "class_name": "person",
            "confidence": 0.91,
            "bbox": [10, 20, 50, 120],
            "label": "ID:006 Person",
            "status": "NORMAL",
            "display_label": "Person",
            "box_color_bgr": [0, 255, 0],
        },
        {
            "track_id": "88",
            "identity_id": None,
            "class_name": "car",
            "confidence": 0.95,
            "bbox": [60, 80, 100, 140],
            "label": "ID:000 Car\nRESTRICTED AREA",
            "status": "DANGER",
            "display_label": "RESTRICTED_AREA",
            "box_color_bgr": [0, 0, 255],
        },
    ]

    payload = AIProcessor._build_detection_overlay_payload(
        "camera-1",
        detections,
        (608, 1080, 3),
        frame_sequence=42,
        capture_timestamp_ns=123456789,
        draw_settings={
            "font_scale": 0.4,
            "line_thickness": 2,
            "padding": 3,
        },
    )

    assert payload["camera_id"] == "camera-1"
    assert payload["frame_sequence"] == 42
    assert payload["capture_timestamp_ns"] == 123456789
    assert (payload["frame_width"], payload["frame_height"]) == (1080, 608)
    assert payload["draw_settings"]["line_thickness"] == 2
    assert [
        (detection["class_name"], detection["confidence"], detection["bbox"])
        for detection in payload["detections"]
    ] == [
        ("person", 0.91, [10, 20, 50, 120]),
        ("car", 0.95, [60, 80, 100, 140]),
    ]
    assert payload["detections"][1]["identity_id"] is None
    assert payload["detections"][1]["label"] == "ID:000 Car\nRESTRICTED AREA"
    assert payload["detections"][1]["status"] == "DANGER"
    assert payload["detections"][1]["display_label"] == "RESTRICTED_AREA"
    assert payload["detections"][1]["box_color_rgb"] == [255, 0, 0]


def test_detection_overlay_payload_clears_boxes_when_no_tracks_are_visible():
    payload = AIProcessor._build_detection_overlay_payload(
        "camera-1",
        [],
        (608, 1080, 3),
        frame_sequence=43,
        capture_timestamp_ns=123456790,
        draw_settings={
            "font_scale": 0.4,
            "line_thickness": 2,
            "padding": 3,
        },
    )

    assert payload["camera_id"] == "camera-1"
    assert payload["detections"] == []


def test_new_person_tracks_are_visible_to_the_overlay_on_the_first_frame():
    tracker = TrackerManager()
    tracks = tracker.update(
        [
            {
                "bbox": [10, 20, 50, 120],
                "class_name": "person",
                "confidence": 0.91,
            }
        ]
    )
    active_tracks = tracker.get_active_tracks()

    assert len(tracks) == 1
    assert len(active_tracks) == 1
    assert active_tracks[0].lost_frames == 0
    payload = AIProcessor._build_detection_overlay_payload(
        "camera-1",
        [
            {
                "track_id": str(track.track_id),
                "identity_id": None,
                "class_name": track.class_name,
                "confidence": track.confidence,
                "bbox": track.bbox,
                "label": AIProcessor._format_overlay_label(
                    track.track_id, track.class_name
                ),
                "status": "NORMAL",
                "display_label": track.class_name,
                "box_color_bgr": [0, 255, 0],
            }
            for track in active_tracks
        ],
        (608, 1080, 3),
        frame_sequence=1,
        capture_timestamp_ns=123456789,
        draw_settings={
            "font_scale": 0.4,
            "line_thickness": 2,
            "padding": 3,
        },
    )
    assert payload["detections"][0]["bbox"] == [10, 20, 50, 120]


def test_iou_tracker_uses_current_detector_bbox_without_smoothing():
    tracker = TrackerManager()
    first_bbox = [10, 20, 50, 120]
    moved_bbox = [18, 20, 58, 120]

    track = tracker.update(
        [{"bbox": first_bbox, "class_name": "person", "confidence": 0.91}]
    )[0]
    moved_track = tracker.update(
        [{"bbox": moved_bbox, "class_name": "person", "confidence": 0.93}]
    )[0]

    assert moved_track.track_id == track.track_id
    assert moved_track.bbox == moved_bbox
    assert moved_track.confidence == 0.93


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
