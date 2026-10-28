import os
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ai.processor import AIProcessor


FEATURE_SETTINGS = (
    "loitering_enabled",
    "crowd_density_enabled",
    "restricted_area_enabled",
    "fire_detection_enabled",
    "smoke_detection_enabled",
)


def test_runtime_settings_preserve_feature_flags_and_abandoned_bag():
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

    for setting in FEATURE_SETTINGS:
        assert getattr(snapshot, setting) is True
    assert snapshot.abandoned_bag_enabled is True
    assert snapshot.abandoned_bag_seconds == 60
    assert snapshot.wrong_direction_enabled is True


@pytest.mark.parametrize("disabled_setting", FEATURE_SETTINGS)
def test_runtime_feature_settings_can_be_disabled_independently(disabled_setting):
    settings = SimpleNamespace(
        owner_id="owner-1",
        **{setting: setting != disabled_setting for setting in FEATURE_SETTINGS},
    )

    snapshot = AIProcessor._snapshot_camera_settings(settings)

    for setting in FEATURE_SETTINGS:
        assert getattr(snapshot, setting) is (setting != disabled_setting)


@pytest.mark.parametrize(
    ("label", "settings", "expected"),
    [
        (
            "fire",
            SimpleNamespace(
                fire_detection_enabled=True,
                smoke_detection_enabled=False,
            ),
            True,
        ),
        (
            "smoke",
            SimpleNamespace(
                fire_detection_enabled=True,
                smoke_detection_enabled=False,
            ),
            False,
        ),
        (
            "fire",
            SimpleNamespace(
                fire_detection_enabled=False,
                smoke_detection_enabled=True,
            ),
            False,
        ),
        (
            "smoke",
            SimpleNamespace(
                fire_detection_enabled=False,
                smoke_detection_enabled=True,
            ),
            True,
        ),
    ],
)
def test_fire_and_smoke_processing_flags_are_independent(label, settings, expected):
    assert AIProcessor._is_fire_smoke_enabled(label, settings) is expected


def test_runtime_settings_keep_abandoned_bag_disabled_when_original_setting_is_false():
    settings = SimpleNamespace(
        owner_id="owner-1",
        abandoned_bag_enabled=False,
    )

    snapshot = AIProcessor._snapshot_camera_settings(settings)

    assert snapshot.abandoned_bag_enabled is False
