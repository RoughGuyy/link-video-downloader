from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import requests


USER_AGENT = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) "
    "AppleWebKit/605.1.15 Version/18.0 Mobile/15E148 Safari/604.1"
)


class XiaohongshuError(RuntimeError):
    """Raised when a public Xiaohongshu page cannot be parsed or downloaded."""


@dataclass(frozen=True)
class VideoStream:
    urls: tuple[str, ...]
    codec: str
    format_id: str = "unknown"
    width: int = 0
    height: int = 0
    bitrate: int = 0
    size: int = 0

    @property
    def pixels(self) -> int:
        return self.width * self.height


@dataclass(frozen=True)
class XiaohongshuMedia:
    title: str
    note_id: str | None
    streams: tuple[VideoStream, ...]


def _normalise_embedded_json(text: str) -> str:
    replacements = {
        r"\u002F": "/",
        r"\u002f": "/",
        r"\u0026": "&",
        r"\u003D": "=",
        r"\u003d": "=",
        r"\u003F": "?",
        r"\u003f": "?",
        r"\/": "/",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def extract_note_id(url: str) -> str | None:
    match = re.search(r"/(?:explore|discovery/item)/([0-9a-fA-F]{24})(?:[/?#]|$)", url)
    return match.group(1).lower() if match else None


def _relevant_page_slice(html: str, note_id: str | None) -> str:
    if not note_id:
        return html
    positions = [match.start() for match in re.finditer(re.escape(note_id), html, re.I)]
    if not positions:
        return html
    stream_marker = '"stream":{"h264"'
    best_position = min(
        positions,
        key=lambda pos: (
            html.find(stream_marker, pos) < 0,
            abs(html.find(stream_marker, pos) - pos) if html.find(stream_marker, pos) >= 0 else 10**9,
        ),
    )
    return html[max(0, best_position - 5_000) : best_position + 180_000]


def _decode_stream_arrays(text: str, group: str) -> Iterable[dict]:
    decoder = json.JSONDecoder()
    pattern = re.compile(rf'"{re.escape(group)}"\s*:\s*')
    for match in pattern.finditer(text):
        try:
            value, _ = decoder.raw_decode(text[match.end() :])
        except json.JSONDecodeError:
            continue
        if isinstance(value, list):
            yield from (item for item in value if isinstance(item, dict))


def extract_streams(html: str, note_id: str | None = None) -> list[VideoStream]:
    text = _relevant_page_slice(_normalise_embedded_json(html), note_id)
    streams: list[VideoStream] = []
    seen: set[str] = set()

    for group in ("h264", "h265", "hevc"):
        for item in _decode_stream_arrays(text, group):
            master = item.get("masterUrl") or item.get("master_url")
            backups = item.get("backupUrls") or item.get("backup_urls") or []
            candidates = [master, *backups]
            urls = tuple(
                url for url in candidates if isinstance(url, str) and url.startswith(("http://", "https://"))
            )
            if not urls or urls[0] in seen:
                continue
            seen.add(urls[0])
            codec = str(item.get("videoCodec") or item.get("video_codec") or group).lower()
            streams.append(
                VideoStream(
                    urls=urls,
                    codec=codec,
                    format_id=str(item.get("streamType") or item.get("stream_type") or group),
                    width=int(item.get("width") or 0),
                    height=int(item.get("height") or 0),
                    bitrate=int(item.get("videoBitrate") or item.get("video_bitrate") or 0),
                    size=int(item.get("size") or 0),
                )
            )
    return streams


def _codec_matches(stream: VideoStream, codec: str) -> bool:
    aliases = {
        "h264": {"h264", "avc", "avc1"},
        "hevc": {"h265", "hevc", "hev1", "hvc1"},
    }
    return stream.codec in aliases.get(codec, {codec})


def select_stream(
    streams: list[VideoStream],
    max_height: int | None = None,
    codec: str = "auto",
    format_id: str | None = None,
) -> VideoStream:
    if not streams:
        raise XiaohongshuError("页面中没有找到可下载的视频流；链接可能已失效或需要登录")

    def score(stream: VideoStream) -> tuple[int, int, int]:
        return stream.pixels, stream.bitrate, stream.size

    if format_id:
        exact = [stream for stream in streams if stream.format_id == format_id]
        if not exact:
            available = ", ".join(stream.format_id for stream in streams)
            raise XiaohongshuError(f"未找到格式 {format_id}；可用格式：{available}")
        return max(exact, key=score)

    candidates = streams
    if max_height:
        within_limit = [stream for stream in candidates if stream.height and stream.height <= max_height]
        candidates = within_limit or [min(candidates, key=lambda stream: stream.height or 10**9)]
    if codec != "auto":
        matching_codec = [stream for stream in candidates if _codec_matches(stream, codec)]
        candidates = matching_codec or candidates
    return max(candidates, key=score)


def _extract_title(html: str, note_id: str | None) -> str:
    text = _relevant_page_slice(_normalise_embedded_json(html), note_id)
    match = re.search(r'"title"\s*:\s*("(?:\\.|[^"\\])*")', text)
    if match:
        try:
            title = json.loads(match.group(1)).strip()
            if title:
                return title
        except json.JSONDecodeError:
            pass
    return f"xiaohongshu_{note_id or 'video'}"


def _safe_filename(value: str, max_length: int = 90) -> str:
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value)
    value = re.sub(r"\s+", " ", value).strip(" .")
    return (value[:max_length].rstrip(" .") or "xiaohongshu_video") + ".mp4"


def _https_first(urls: Iterable[str]) -> list[str]:
    converted = ["https://" + url[7:] if url.startswith("http://") else url for url in urls]
    return list(dict.fromkeys(converted))


def probe_xiaohongshu(
    url: str,
    session: requests.Session | None = None,
) -> XiaohongshuMedia:
    session = session or requests.Session()
    headers = {"User-Agent": USER_AGENT, "Referer": "https://www.xiaohongshu.com/"}
    try:
        response = session.get(url, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise XiaohongshuError(f"无法打开小红书页面：{exc}") from exc

    note_id = extract_note_id(response.url) or extract_note_id(url)
    streams = extract_streams(response.text, note_id)
    if not streams:
        raise XiaohongshuError("页面中没有找到可下载的视频流；链接可能已失效或需要登录")
    return XiaohongshuMedia(
        title=_extract_title(response.text, note_id),
        note_id=note_id,
        streams=tuple(streams),
    )


def download_xiaohongshu(
    url: str,
    output_dir: Path,
    max_height: int | None = None,
    codec: str = "auto",
    format_id: str | None = None,
    session: requests.Session | None = None,
) -> Path:
    session = session or requests.Session()
    headers = {"User-Agent": USER_AGENT, "Referer": "https://www.xiaohongshu.com/"}
    media_info = probe_xiaohongshu(url, session)
    selected = select_stream(list(media_info.streams), max_height, codec, format_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / _safe_filename(media_info.title)
    temporary = destination.with_suffix(destination.suffix + ".part")

    last_error: Exception | None = None
    for media_url in _https_first(selected.urls):
        try:
            with session.get(media_url, headers=headers, stream=True, timeout=(15, 90)) as media:
                media.raise_for_status()
                with temporary.open("wb") as file_handle:
                    for chunk in media.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            file_handle.write(chunk)
            if temporary.stat().st_size < 1024:
                raise XiaohongshuError("下载到的文件异常小")
            os.replace(temporary, destination)
            return destination
        except (OSError, requests.RequestException, XiaohongshuError) as exc:
            last_error = exc
            temporary.unlink(missing_ok=True)

    raise XiaohongshuError(f"所有视频地址均下载失败：{last_error}")
