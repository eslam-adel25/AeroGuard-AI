from __future__ import annotations

import re
from typing import Optional


def parse_user_agent(user_agent: Optional[str]) -> dict[str, Optional[str]]:
    if not user_agent:
        return {
            "operating_system": "Unknown",
            "browser": "Unknown",
            "device_category": "Desktop",
            "device_type": "Unknown device",
            "device_model": None,
        }

    ua = user_agent.lower()

    browser = "Unknown"
    if "edg/" in ua or "edge/" in ua or "edgios" in ua:
        browser = "Edge"
    elif "chrome" in ua:
        browser = "Chrome"
    elif "firefox" in ua:
        browser = "Firefox"
    elif "safari" in ua and "chrome" not in ua:
        browser = "Safari"
    elif "samsungbrowser" in ua:
        browser = "Samsung Internet"
    elif "opr/" in ua or "opera" in ua:
        browser = "Opera"
    elif "brave" in ua:
        browser = "Brave"

    operating_system = "Unknown"
    device_model = None
    device_category = "Desktop"

    if "iphone" in ua:
        operating_system = "iPhone"
        device_model = "iPhone"
        device_category = "Mobile"
    elif "ipad" in ua:
        operating_system = "iPad"
        device_model = "iPad"
        device_category = "Tablet"
    elif "android" in ua:
        operating_system = "Android"
        device_category = "Mobile"
        if "tablet" in ua:
            device_category = "Tablet"
    elif "windows" in ua:
        if "windows nt 6.1" in ua:
            operating_system = "Windows 7"
        elif "windows nt 6.2" in ua:
            operating_system = "Windows 8"
        elif "windows nt 6.3" in ua:
            operating_system = "Windows 8.1"
        elif "windows nt 10.0" in ua:
            operating_system = "Windows 11"
        else:
            operating_system = "Windows"
    elif "mac os x" in ua or "macintosh" in ua:
        operating_system = "macOS"
    elif "linux" in ua:
        operating_system = "Linux"
    elif "ubuntu" in ua:
        operating_system = "Ubuntu"
    elif "cros" in ua:
        operating_system = "ChromeOS"

    if operating_system in {"Unknown"}:
        if "mobile" in ua:
            device_category = "Mobile"
        elif "tablet" in ua:
            device_category = "Tablet"

    if operating_system in {"macOS", "Windows 11", "Windows 10", "Windows", "Ubuntu", "Linux", "ChromeOS"}:
        device_category = "Desktop"

    device_type = f"{operating_system} • {browser}" if operating_system != "Unknown" and browser != "Unknown" else "Unknown device"

    return {
        "operating_system": operating_system,
        "browser": browser,
        "device_category": device_category,
        "device_type": device_type,
        "device_model": device_model,
    }
