from __future__ import annotations

from enum import Enum
from urllib.parse import urlparse


class UnsupportedURL(ValueError):
    """Raised when a URL is not from a supported platform."""


class Platform(str, Enum):
    XIAOHONGSHU = "xiaohongshu"
    BILIBILI = "bilibili"
    YOUTUBE = "youtube"


def _matches(hostname: str, domain: str) -> bool:
    return hostname == domain or hostname.endswith(f".{domain}")


def detect_platform(url: str) -> Platform:
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise UnsupportedURL("请输入完整的 http:// 或 https:// 链接")

    hostname = parsed.hostname.lower().rstrip(".")
    if _matches(hostname, "xiaohongshu.com") or _matches(hostname, "xhslink.com"):
        return Platform.XIAOHONGSHU
    if _matches(hostname, "bilibili.com") or _matches(hostname, "b23.tv"):
        return Platform.BILIBILI
    if any(
        _matches(hostname, domain)
        for domain in ("youtube.com", "youtu.be", "youtube-nocookie.com")
    ):
        return Platform.YOUTUBE
    raise UnsupportedURL(f"暂不支持该网站：{hostname}")

