from app.utils.device_info import parse_user_agent


def test_parses_windows_chrome_user_agent() -> None:
    info = parse_user_agent(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    )

    assert info["operating_system"] == "Windows 11"
    assert info["browser"] == "Chrome"
    assert info["device_category"] == "Desktop"
    assert info["device_type"] == "Windows 11 • Chrome"


def test_parses_ios_safari_user_agent() -> None:
    info = parse_user_agent(
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 "
        "Mobile/15E148 Safari/604.1"
    )

    assert info["operating_system"] == "iPhone"
    assert info["browser"] == "Safari"
    assert info["device_category"] == "Mobile"
    assert info["device_type"] == "iPhone • Safari"
