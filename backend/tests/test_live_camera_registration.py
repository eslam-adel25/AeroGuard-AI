import asyncio

import pytest

from app.api.v1 import cameras


def test_validate_live_rtsp_url_accepts_rtsp_and_rtsps():
    assert cameras._validate_live_rtsp_url("rtsp://camera.example/live") == "rtsp://camera.example/live"
    assert cameras._validate_live_rtsp_url("rtsps://camera.example/live") == "rtsps://camera.example/live"


@pytest.mark.parametrize("url", ["", "http://camera.example/live", "rtsp://"])
def test_validate_live_rtsp_url_rejects_invalid_urls(url):
    with pytest.raises(cameras.HTTPException) as error:
        cameras._validate_live_rtsp_url(url)

    assert error.value.status_code == 400


class FakeCapture:
    def __init__(self, opened=True, frame=True):
        self.opened = opened
        self.frame = frame
        self.released = False

    def set(self, *_args):
        return True

    def open(self, _url):
        return self.opened

    def isOpened(self):
        return self.opened

    def read(self):
        if not self.frame:
            return False, None
        import numpy as np
        return True, np.zeros((2, 2, 3), dtype=np.uint8)

    def release(self):
        self.released = True


def test_probe_requires_open_stream_and_real_frame(monkeypatch):
    opened_capture = FakeCapture(opened=True, frame=True)
    monkeypatch.setattr(cameras.cv2, "VideoCapture", lambda: opened_capture)
    assert cameras._probe_live_rtsp("rtsp://camera.example/live") is True
    assert opened_capture.released is True

    no_frame_capture = FakeCapture(opened=True, frame=False)
    monkeypatch.setattr(cameras.cv2, "VideoCapture", lambda: no_frame_capture)
    assert cameras._probe_live_rtsp("rtsp://camera.example/live") is False
    assert no_frame_capture.released is True


def test_verify_live_rtsp_reports_probe_failure(monkeypatch):
    monkeypatch.setattr(cameras, "_probe_live_rtsp", lambda _url: False)

    with pytest.raises(cameras.HTTPException) as error:
        asyncio.run(cameras._verify_live_rtsp("rtsp://camera.example/live"))

    assert error.value.status_code == 400
