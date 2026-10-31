"""CPU-only media IO integration smoke with synthetic test cards, NEVER real AI footage.

Tests that existing OneFlow stitching and ffprobe inspection actually run when
real clips later arrive from Runpod. No network, GPU, paid models, or publishing.
"""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from oneflow.core import FlowError, assemble, audit, config, primary_media, probe


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),
                     "ffmpeg/ffprobe required for real media smoke")
class OneFlowFFmpegIntegrationTests(unittest.TestCase):
    def fake_clip(self, dest, color, with_audio=True):
        cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
               "-f", "lavfi", "-i", f"color=c={color}:s=320x240:r=24:d=1.3"]
        if with_audio:
            cmd += ["-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=1.3"]
        cmd += ["-t", "1.3", "-c:v", "libx264", "-preset", "ultrafast",
                "-crf", "32", "-pix_fmt", "yuv420p"]
        if with_audio:
            cmd += ["-c:a", "aac", "-b:a", "64k"]
        cmd += [str(dest)]
        subprocess.run(cmd, check=True, timeout=40, capture_output=True)

    def test_two_real_mp4_test_cards_can_be_joined_and_technically_reviewed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "media").mkdir()
            self.fake_clip(root / "s01.mp4", "blue")
            self.fake_clip(root / "s02.mp4", "orange")
            manifest = {"ratio": "1:1", "seconds": 2,
                        "shots": [
                            {"id": "S01", "seconds": 1, "video": "s01.mp4",
                             "image": None, "audio": None, "normalized": None},
                            {"id": "S02", "seconds": 1, "video": "s02.mp4",
                             "image": None, "audio": None, "normalized": None}]}
            cfg = config()
            cfg["fps"] = 24
            movie = assemble(root, manifest, cfg)
            self.assertTrue(movie.exists())
            result = probe(movie)
            self.assertIsNotNone(primary_media(result, "video"))
            self.assertIsNotNone(primary_media(result, "audio"))
            self.assertAlmostEqual(float(result["format"]["duration"]), 2.0, delta=.18)
            checks = audit(root, manifest, cfg, movie)
            self.assertEqual(checks["status"], "REVIEW_REQUIRED")
            self.assertNotEqual(checks["status"], "PASS")
            self.assertIn("final_human_signoff", checks["manual_review_required"])
            self.assertTrue((root / "qc.json").exists())

    def test_missing_audio_is_rejected_instead_of_faked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "media").mkdir()
            self.fake_clip(root / "no-audio.mp4", "green", with_audio=False)
            manifest = {"ratio": "1:1", "seconds": 1,
                        "shots": [{"id": "S01", "seconds": 1, "video": "no-audio.mp4",
                                   "image": None, "audio": None, "normalized": None}]}
            with self.assertRaisesRegex(FlowError, "has no sound effects"):
                assemble(root, manifest, config())


if __name__ == "__main__":
    unittest.main()
