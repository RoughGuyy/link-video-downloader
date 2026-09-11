import unittest

from linkvideo.platforms import Platform, UnsupportedURL, detect_platform


class DetectPlatformTests(unittest.TestCase):
    def test_xiaohongshu_urls(self):
        self.assertEqual(
            detect_platform("https://www.xiaohongshu.com/explore/abc"),
            Platform.XIAOHONGSHU,
        )
        self.assertEqual(detect_platform("https://xhslink.com/a/abc"), Platform.XIAOHONGSHU)

    def test_bilibili_urls(self):
        self.assertEqual(detect_platform("https://www.bilibili.com/video/BV123"), Platform.BILIBILI)
        self.assertEqual(detect_platform("https://b23.tv/abc"), Platform.BILIBILI)

    def test_youtube_urls(self):
        self.assertEqual(detect_platform("https://youtu.be/abc"), Platform.YOUTUBE)
        self.assertEqual(detect_platform("https://www.youtube.com/watch?v=abc"), Platform.YOUTUBE)

    def test_rejects_lookalike_and_invalid_urls(self):
        with self.assertRaises(UnsupportedURL):
            detect_platform("https://youtube.com.example.org/watch?v=abc")
        with self.assertRaises(UnsupportedURL):
            detect_platform("not-a-url")


if __name__ == "__main__":
    unittest.main()

