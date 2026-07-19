import pytest

from app.ai.processor import _normalize_zone_coords


def test_normalize_zone_coords_extracts_points_from_wrapped_payload():
    payload = {
        "points": [[10, 20], [30, 40]],
        "video_width": 640,
        "video_height": 480,
    }

    coords = _normalize_zone_coords(
        payload,
        camera_id="camera-1",
        annotation_id="zone-1",
        rule_type="restricted_area",
    )

    assert coords == [[10, 20], [30, 40]]


def test_normalize_zone_coords_leaves_plain_list_unchanged():
    payload = [[10, 20], [30, 40]]

    coords = _normalize_zone_coords(
        payload,
        camera_id="camera-1",
        annotation_id="zone-2",
        rule_type="tripwire",
    )

    assert coords == [[10, 20], [30, 40]]
