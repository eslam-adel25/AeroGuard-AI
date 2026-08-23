import os

os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost/db")

import numpy as np

from app.ai.processor import _line_coords_in_frame


def test_normalized_rule_line_coordinates_use_frame_dimensions() -> None:
    result = _line_coords_in_frame([[0.25, 0.5], [0.75, 0.5]], (608, 1080, 3))

    np.testing.assert_allclose(result, [[270.0, 304.0], [810.0, 304.0]])


def test_pixel_rule_line_coordinates_remain_unchanged() -> None:
    result = _line_coords_in_frame([[270, 304], [810, 304]], (608, 1080, 3))

    np.testing.assert_allclose(result, [[270.0, 304.0], [810.0, 304.0]])
