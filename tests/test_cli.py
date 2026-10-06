import unittest

from unittest.mock import patch

from linkvideo.cli import (
    DOWNLOAD_RETRIES,
    _build_ytdlp_format,
    _download_with_ytdlp,
    _find_ffmpeg,
    _height_limit,
    _retry_sleep,
)


class QualitySelectorTests(unittest.TestCase):
    def test_height_limit(self):
        self.assertIsNone(_height_limit("best"))
        self.assertEqual(_height_limit("1080p"), 1080)

    def test_ffmpeg_selector_limits_height(self):
        selector = _build_ytdlp_format("720p", "auto", True)
        self.assertIn("height<=720", selector)
        self.assertIn("+ba", selector)

    def test_h264_selector_and_single_file_fallback(self):
        selector = _build_ytdlp_format("1080p", "h264", False)
        self.assertIn("vcodec^=avc", selector)
        self.assertIn("ext=mp4", selector)

    @patch("linkvideo.cli.shutil.which", return_value="C:/ffmpeg/bin/ffmpeg.exe")
    def test_prefers_system_ffmpeg(self, _mock_which):
        self.assertEqual(_find_ffmpeg(), "C:/ffmpeg/bin/ffmpeg.exe")

    def test_retry_sleep_uses_capped_exponential_backoff(self):
        self.assertEqual([_retry_sleep(i) for i in range(1, 7)], [1, 2, 4, 8, 10, 10])

    @patch("linkvideo.cli._find_ffmpeg", return_value="C:/ffmpeg/bin/ffmpeg.exe")
    def test_ytdlp_download_enables_retries_and_resume(self, _mock_ffmpeg):
        captured_options = {}

        class FakeYoutubeDL:
            def __init__(self, options):
                captured_options.update(options)

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def download(self, _urls):
                return 0

        fake_yt_dlp = type(
            "FakeYtDlp",
            (),
            {
                "YoutubeDL": FakeYoutubeDL,
                "utils": type("Utils", (), {"DownloadError": RuntimeError}),
            },
        )

        with patch.dict("sys.modules", {"yt_dlp": fake_yt_dlp}):
            _download_with_ytdlp(
                "https://www.bilibili.com/video/BV123",
                self.temp_dir,
                "best",
                "auto",
                None,
                False,
            )

        self.assertTrue(captured_options["continuedl"])
        self.assertEqual(captured_options["retries"], DOWNLOAD_RETRIES)
        self.assertEqual(captured_options["fragment_retries"], DOWNLOAD_RETRIES)
        self.assertEqual(captured_options["socket_timeout"], 30)
        self.assertEqual(captured_options["retry_sleep_functions"]["http"](4), 8)

    def setUp(self):
        from tempfile import TemporaryDirectory

        self._temporary_directory = TemporaryDirectory()
        from pathlib import Path

        self.temp_dir = Path(self._temporary_directory.name)

    def tearDown(self):
        self._temporary_directory.cleanup()


if __name__ == "__main__":
    unittest.main()
