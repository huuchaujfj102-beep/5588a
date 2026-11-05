import json
import tempfile
import unittest
from pathlib import Path

from oneflow.core import DEFAULT, create
from oneflow.cinematic_image_rules import GLOBAL_PREFIX
from oneflow.cinematic_i2v_rules import TEMPORAL_PREFIX


class XinghuoPolicySyncTests(unittest.TestCase):
    def test_one_sentence_plan_inherits_three_document_rules(self):
        with tempfile.TemporaryDirectory() as temp:
            job = create("A golden warrior walks through a temple", 10, "9:16",
                         ["douyin"], temp, DEFAULT)
            manifest = json.loads((Path(job) / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["production_policy"]["name"], "XINGHUO_3_ONEFLOW_CINEMATIC")
            self.assertEqual(len(manifest["shots"]), 2)
            for shot in manifest["shots"]:
                self.assertTrue(shot["image_prompt"].startswith(GLOBAL_PREFIX))
                self.assertTrue(shot["visual_prompt"].startswith(TEMPORAL_PREFIX))
                self.assertIn("anatomical defect", shot["image_negative_prompt"])
                self.assertIn("temporal flicker", shot["video_negative_prompt"])
                self.assertEqual(shot["source_image_review_status"], "REVIEW_REQUIRED")
                self.assertIsNone(shot["image"])
                self.assertIsNone(shot["video"])
            self.assertEqual(manifest["status"], "PLANNED")


if __name__ == "__main__":
    unittest.main()
