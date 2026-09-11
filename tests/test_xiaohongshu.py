import json
import unittest

from linkvideo.xiaohongshu import extract_note_id, extract_streams, select_stream


NOTE_ID = "6a810393000000002c000a24"


class XiaohongshuParserTests(unittest.TestCase):
    def setUp(self):
        payload = {
            "noteId": NOTE_ID,
            "video": {
                "media": {
                    "stream": {
                        "h264": [
                            {
                                "masterUrl": "http://cdn.example/259/video.mp4?sign=abc",
                                "backupUrls": ["http://backup.example/259/video.mp4"],
                                "videoCodec": "h264",
                                "streamType": 259,
                                "width": 720,
                                "height": 1280,
                                "videoBitrate": 1200,
                                "size": 22_000_000,
                            }
                        ],
                        "h265": [
                            {
                                "masterUrl": "http://cdn.example/309/video.mp4?sign=xyz",
                                "videoCodec": "hevc",
                                "streamType": 309,
                                "width": 1080,
                                "height": 1920,
                                "videoBitrate": 1800,
                                "size": 25_000_000,
                            }
                        ],
                    }
                }
            },
        }
        embedded = json.dumps(payload, separators=(",", ":")).replace("/", r"\u002F")
        self.html = f"<script>window.__INITIAL_STATE__={embedded}</script>"

    def test_extract_note_id(self):
        self.assertEqual(
            extract_note_id(f"https://www.xiaohongshu.com/explore/{NOTE_ID}?x=1"),
            NOTE_ID,
        )

    def test_extracts_h264_and_hevc(self):
        streams = extract_streams(self.html, NOTE_ID)
        self.assertEqual(len(streams), 2)
        self.assertEqual({stream.codec for stream in streams}, {"h264", "hevc"})
        self.assertEqual({stream.format_id for stream in streams}, {"259", "309"})
        self.assertTrue(streams[0].urls[0].startswith("http://"))

    def test_quality_strategy(self):
        streams = extract_streams(self.html, NOTE_ID)
        self.assertEqual(select_stream(streams, codec="h264").codec, "h264")
        self.assertEqual(select_stream(streams).codec, "hevc")
        self.assertEqual(select_stream(streams, max_height=720).codec, "h264")
        self.assertEqual(select_stream(streams, codec="hevc").codec, "hevc")
        self.assertEqual(select_stream(streams, format_id="259").format_id, "259")


if __name__ == "__main__":
    unittest.main()
