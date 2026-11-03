"""Unbilled end-to-end media smoke: real FFmpeg, real AAC and watermark."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from oneflow.vidu_q3 import probe_mp4, render_portrait


class ViduMediaSmoke(unittest.TestCase):
    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),
                         "FFmpeg tools not installed")
    def test_portrait_watermark_and_audio_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "provider-test.mp4"
            target = Path(tmp) / "final-draft.mp4"
            subprocess.run([
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-f", "lavfi", "-i", "testsrc2=size=640x360:rate=24:duration=1",
                "-f", "lavfi", "-i", "sine=frequency=190:duration=1",
                "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-shortest", str(source)
            ], check=True, capture_output=True, timeout=45)
            src_info = probe_mp4(source)
            self.assertTrue(src_info["has_audio"])
            output = render_portrait(source, target, seconds=1)
            self.assertTrue(target.exists())
            self.assertGreater(target.stat().st_size, 2000)
            self.assertEqual((output["width"], output["height"]), (1080, 1920))
            self.assertTrue(output["has_audio"])
            self.assertLess(abs(output["duration"] - 1), 0.5)


if __name__ == "__main__":
    unittest.main()
