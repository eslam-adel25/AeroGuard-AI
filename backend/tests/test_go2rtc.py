from app.services.go2rtc import (
    Go2RTCService,
    build_go2rtc_live_url,
    build_go2rtc_source_url,
    build_go2rtc_webrtc_url,
)


def test_go2rtc_urls_use_documented_paths_and_stable_stream_name(monkeypatch):
    monkeypatch.setenv("GO2RTC_BASE_URL", "https://video.example/rtc")
    monkeypatch.setenv("GO2RTC_RTSP_URL", "rtsp://127.0.0.1:8556")

    assert (
        build_go2rtc_webrtc_url("cam/one")
        == "wss://video.example/rtc/api/ws?src=cam%2Fone"
    )
    assert (
        build_go2rtc_live_url("cam/one")
        == "https://video.example/rtc/api/stream.m3u8?src=cam%2Fone"
    )
    assert (
        build_go2rtc_source_url("cam/one")
        == "rtsp://127.0.0.1:8556/cam%2Fone"
    )


def test_register_stream_uses_put_for_new_and_patch_for_existing(monkeypatch):
    service = Go2RTCService()
    requests = []
    responses = iter(({}, {"camera-1": {"producers": []}}))

    monkeypatch.setattr(service, "start", lambda: None)

    def request(method, path, query=None):
        requests.append((method, path, query))
        if method == "GET":
            return next(responses)
        return None

    monkeypatch.setattr(service, "_request", request)

    service.register_stream("camera-1", "rtsp://camera.example/live")
    service.register_stream("camera-1", "rtsp://camera.example/updated")

    assert requests == [
        ("GET", "/api/streams", None),
        (
            "PUT",
            "/api/streams",
            {"src": "rtsp://camera.example/live", "name": "camera-1"},
        ),
        ("GET", "/api/streams", None),
        (
            "PATCH",
            "/api/streams",
            {"src": "rtsp://camera.example/updated", "name": "camera-1"},
        ),
    ]
