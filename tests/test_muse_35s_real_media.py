"""CPU-only smoke test of a *real encoded* portrait adaptation, no AI calls.

This exercises the actual FFmpeg command, not a mocked media operation.
"""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from oneflow.muse_35s import _portrait_from_square
from oneflow.muse_10s import last_frame


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),
                     "ffmpeg and ffprobe required for actual media smoke")
class Muse35RealMediaSmoke(unittest.TestCase):
    def test_square_clip_to_portrait_video_and_real_tail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = root / "provider-square.mp4"
            subprocess.run([
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-f", "lavfi", "-i", "testsrc2=size=256x256:rate=12",
                "-t", "1.2", "-an", "-c:v", "libx264", "-preset", "ultrafast",
                "-pix_fmt", "yuv420p", str(raw)
            ], check=True, timeout=40)
            portrait = _portrait_from_square(raw, root / "adapted.mp4")
            self.assertTrue(portrait.exists())
            stream = subprocess.check_output([
                "ffprobe", "-v", "error", "-show_streams", "-show_format",
                "-of", "json", str(portrait)
            ], timeout=20)
            info = json.loads(stream)
            video = next(s for s in info["streams"] if s["codec_type"] == "video")
            self.assertEqual((video["width"], video["height"]), (1080, 1920))
            self.assertGreater(float(info["format"]["duration"]), 1.0)
            next_frame = last_frame(raw, root / "S02-start-from-prior-tail.png")
            self.assertGreater(next_frame.stat().st_size, 64)
            # The second image must originate from real decoded MP4 frames.


if __name__ == "__main__":
    unittest.main()
