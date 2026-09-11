import unittest

from unittest.mock import patch

from linkvideo.cli import _build_ytdlp_format, _find_ffmpeg, _height_limit


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


if __name__ == "__main__":
    unittest.main()
