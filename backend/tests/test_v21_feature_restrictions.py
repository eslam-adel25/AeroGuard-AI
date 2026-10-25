import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ai.processor import AIProcessor


def test_runtime_settings_force_second_term_features_off_and_preserve_abandoned_bag():
    settings = SimpleNamespace(
        owner_id="owner-1",
        loitering_enabled=True,
        crowd_density_enabled=True,
        restricted_area_enabled=True,
        fire_detection_enabled=True,
        smoke_detection_enabled=True,
        abandoned_bag_enabled=True,
        abandoned_bag_seconds=20,
        wrong_direction_enabled=True,
    )

    snapshot = AIProcessor._snapshot_camera_settings(settings)

    assert snapshot.loitering_enabled is False
    assert snapshot.crowd_density_enabled is False
    assert snapshot.restricted_area_enabled is False
    assert snapshot.fire_detection_enabled is False
    assert snapshot.smoke_detection_enabled is False
    assert snapshot.abandoned_bag_enabled is True
    assert snapshot.abandoned_bag_seconds == 20
    assert snapshot.wrong_direction_enabled is True


def test_runtime_settings_keep_abandoned_bag_disabled_when_original_setting_is_false():
    settings = SimpleNamespace(
        owner_id="owner-1",
        abandoned_bag_enabled=False,
    )

    snapshot = AIProcessor._snapshot_camera_settings(settings)

    assert snapshot.abandoned_bag_enabled is False
