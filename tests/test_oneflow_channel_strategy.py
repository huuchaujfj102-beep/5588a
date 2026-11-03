import tempfile
import unittest
from pathlib import Path

from oneflow.channel_strategy import ORDER, build, main

class StrategyTests(unittest.TestCase):
    def test_five_distinct_native_treatments(self):
        data = build("未来超跑在夕阳山道上起步并高速掠过")
        self.assertEqual(set(data["content_variants"]), set(ORDER))
        self.assertFalse(data["viral_guarantee"])
        hooks = [v["opening_hook"] for v in data["content_variants"].values()]
        self.assertEqual(len(set(hooks)), 5)
        titles = [v["suggested_title"] for v in data["content_variants"].values()]
        self.assertEqual(len(set(titles)), 5)
        self.assertEqual({v["publication_status"] for v in data["content_variants"].values()}, {"NOT_SUBMITTED"})
        self.assertEqual({v["release_status"] for v in data["content_variants"].values()}, {"NOT_GENERATED"})
        self.assertEqual({v["ratio"] for v in data["content_variants"].values()}, {"9:16"})
        self.assertTrue(all(len(v["scene_plan"]) == 3 for v in data["content_variants"].values()))
    def test_input_rejected(self):
        with self.assertRaises(ValueError):
            build("a")
        with self.assertRaises(ValueError):
            build("Supercar cinematic", niche="medical")
    def test_file_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            main(["--idea", "超跑夕阳疾驰", "--out", tmp])
            self.assertTrue((Path(tmp) / "strategy.json").exists())
            self.assertTrue((Path(tmp) / "youtube-creative-brief.json").exists())

if __name__ == "__main__":
    unittest.main()
