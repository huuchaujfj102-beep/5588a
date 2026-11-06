"""Real FFmpeg crops verify evidence coverage; no VLM or paid calls."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from oneflow.visual_review import snapshots, validate_review, VisualReviewError
from oneflow.continuity_rules import REVIEW_CHECKLIST


class ReviewEvidenceTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("ffmpeg"), "FFmpeg required")
    def test_two_moments_have_separate_lower_frame_evidence(self):
        with tempfile.TemporaryDirectory() as root:
            clip = Path(root) / "clip.mp4"
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi",
                            "-i", "testsrc2=size=160x240:rate=10", "-t", "0.8",
                            "-c:v", "mpeg4", str(clip)], check=True, timeout=30)
            frames = snapshots(clip, Path(root) / "views", "S01")
            self.assertEqual([p.name for p in frames], ["S01-head-review.jpg",
                "S01-tail-review.jpg", "S01-head-feet-review.jpg", "S01-tail-feet-review.jpg"])
            self.assertTrue(all(p.stat().st_size > 0 for p in frames))
            self.assertNotEqual(frames[0].read_bytes(), frames[2].read_bytes())
        self.assertIn("no extra time coverage", REVIEW_CHECKLIST)

    def test_empty_finding_is_not_evidence(self):
        with self.assertRaises(VisualReviewError):
            validate_review({"findings": [{"severity": "warning", "description": " "}],
                             "uncertainties": []})


if __name__ == "__main__":
    unittest.main()
