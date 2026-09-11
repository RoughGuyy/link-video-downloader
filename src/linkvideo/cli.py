from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from . import __version__
from .platforms import Platform, UnsupportedURL, detect_platform
from .xiaohongshu import XiaohongshuError, download_xiaohongshu, probe_xiaohongshu


QUALITY_CHOICES = ("best", "2160p", "1440p", "1080p", "720p", "480p", "360p")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="linkvideo",
        description="输入一个公开链接，下载小红书、B站或 YouTube 视频。",
    )
    parser.add_argument("url", nargs="?", help="视频页面或分享链接")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("downloads"),
        help="保存目录（默认：./downloads）",
    )
    parser.add_argument(
        "-q",
        "--quality",
        choices=QUALITY_CHOICES,
        default="best",
        help="最高下载清晰度（默认：best）",
    )
    parser.add_argument(
        "--codec",
        choices=("auto", "h264", "hevc"),
        default="auto",
        help="视频编码偏好；无匹配格式时自动回退（默认：auto）",
    )
    parser.add_argument(
        "-F",
        "--list-formats",
        action="store_true",
        help="仅列出该链接可用的格式和清晰度，不下载",
    )
    parser.add_argument(
        "-f",
        "--format-id",
        help="直接选择 --list-formats 显示的格式编号",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def _height_limit(quality: str) -> int | None:
    return None if quality == "best" else int(quality.removesuffix("p"))


def _build_ytdlp_format(
    quality: str,
    codec: str,
    has_ffmpeg: bool,
) -> str:
    height = "" if quality == "best" else f"[height<={_height_limit(quality)}]"
    codec_filter = {"h264": "[vcodec^=avc]", "hevc": "[vcodec^=hev]"}.get(codec, "")
    if has_ffmpeg:
        preferred = f"bv*{height}{codec_filter}+ba"
        unfiltered = f"bv*{height}+ba"
        return f"{preferred}/{unfiltered}/b{height}/b"
    preferred = f"b{height}{codec_filter}[ext=mp4]"
    return f"{preferred}/b{height}[ext=mp4]/b{height}/b"


def _find_ffmpeg() -> str | None:
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except (ImportError, RuntimeError, OSError):
        return None


def _download_with_ytdlp(
    url: str,
    output_dir: Path,
    quality: str,
    codec: str,
    format_id: str | None,
    list_formats: bool,
) -> None:
    try:
        import yt_dlp
    except ImportError as exc:
        raise RuntimeError("缺少 yt-dlp，请先运行：python -m pip install -e .") from exc

    output_dir.mkdir(parents=True, exist_ok=True)
    ffmpeg_path = _find_ffmpeg()
    has_ffmpeg = ffmpeg_path is not None
    options = {
        "format": format_id or _build_ytdlp_format(quality, codec, has_ffmpeg),
        "merge_output_format": "mp4",
        "outtmpl": str(output_dir / "%(title).120B [%(id)s].%(ext)s"),
        "noplaylist": True,
        "windowsfilenames": True,
    }
    if ffmpeg_path:
        options["ffmpeg_location"] = ffmpeg_path
    if list_formats:
        options.update({"listformats": True, "skip_download": True})
    elif not has_ffmpeg:
        print("提示：FFmpeg 不可用，将下载最佳单文件版本。请重新运行安装程序修复依赖。")
    try:
        with yt_dlp.YoutubeDL(options) as downloader:
            error_code = downloader.download([url])
    except yt_dlp.utils.DownloadError as exc:
        raise RuntimeError(str(exc)) from exc
    if error_code:
        raise RuntimeError(f"yt-dlp 下载失败，退出码：{error_code}")


def _print_xiaohongshu_formats(url: str) -> None:
    media = probe_xiaohongshu(url)
    print(f"标题：{media.title}")
    print("格式ID  编码   分辨率      码率(kbps)  大小(MB)")
    for stream in sorted(media.streams, key=lambda item: (item.pixels, item.bitrate), reverse=True):
        resolution = f"{stream.width}x{stream.height}" if stream.width and stream.height else "未知"
        bitrate = f"{stream.bitrate / 1000:.0f}" if stream.bitrate else "-"
        size = f"{stream.size / 1024 / 1024:.1f}" if stream.size else "-"
        print(f"{stream.format_id:<8} {stream.codec:<6} {resolution:<11} {bitrate:<11} {size}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    url = args.url or input("请粘贴小红书、B站或 YouTube 链接：").strip()
    if not url:
        parser.error("链接不能为空")

    try:
        platform = detect_platform(url)
        print(f"已识别平台：{platform.value}")
        if platform is Platform.XIAOHONGSHU:
            if args.list_formats:
                _print_xiaohongshu_formats(url)
                return 0
            path = download_xiaohongshu(
                url,
                args.output.resolve(),
                max_height=_height_limit(args.quality),
                codec=args.codec,
                format_id=args.format_id,
            )
            print(f"下载完成：{path}")
        else:
            _download_with_ytdlp(
                url,
                args.output.resolve(),
                args.quality,
                args.codec,
                args.format_id,
                args.list_formats,
            )
            if not args.list_formats:
                print(f"下载完成，文件位于：{args.output.resolve()}")
        return 0
    except (UnsupportedURL, XiaohongshuError, RuntimeError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n已取消。", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
