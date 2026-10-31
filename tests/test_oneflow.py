import json
import tempfile
import unittest
from pathlib import Path

from oneflow.core import (FlowError, authorize_publish, approve, config, create,
                          job_root, load_json, produce, publish, describe)
from oneflow.providers import ProviderError, endpoint


class OneFlowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.cfg = config()

    def make_job(self, seconds=35):
        return create("喷气式跑车启动、加速、腾空、尾焰飞向远方", seconds, "9:16",
                      ["youtube", "douyin"], self.root, self.cfg)

    def test_one_sentence_creates_real_manifest_not_video(self):
        root = self.make_job()
        data = load_json(root / "manifest.json")
        self.assertEqual(data["status"], "PLANNED")
        self.assertEqual(sum(s["seconds"] for s in data["shots"]), 35)
        self.assertEqual(len(data["shots"]), 7)
        self.assertEqual(len({s["id"] for s in data["shots"]}), 7)
        self.assertTrue((root / "storyboard.md").is_file())
        self.assertFalse((root / "final-draft.mp4").exists())
        self.assertIsNone(data["approval"])

    def test_no_provider_fails_before_render(self):
        root = self.make_job()
        with self.assertRaisesRegex(FlowError, "Configure real image"):
            produce(root, self.cfg)
        self.assertEqual(load_json(root / "manifest.json")["status"], "PLANNED")

    def test_audio_missing_fails_before_any_generation(self):
        root = self.make_job()
        cfg = {**self.cfg, "image": [{"kind": "comfyui"}],
               "video": [{"kind": "comfyui"}]}
        with self.assertRaisesRegex(FlowError, "sound generation"):
            produce(root, cfg)
        self.assertEqual(load_json(root / "manifest.json")["status"], "PLANNED")

    def test_reviewer_cannot_approve_without_audit(self):
        with self.assertRaisesRegex(FlowError, "Only an audited"):
            approve(self.make_job(), "reviewer", True, True)

    def test_preapproval_publish_is_blocked(self):
        root = self.make_job()
        data = load_json(root / "manifest.json")
        with self.assertRaisesRegex(FlowError, "human approval"):
            authorize_publish(root, data, "youtube")
        with self.assertRaisesRegex(FlowError, "human approval"):
            publish(root, "youtube", self.cfg, True)

    def test_invalid_input_and_platform(self):
        with self.assertRaises(FlowError):
            create("a", 35, "9:16", [], self.root, self.cfg)
        with self.assertRaises(FlowError):
            create("一条短片", 120, "9:16", [], self.root, self.cfg)
        with self.assertRaises(FlowError):
            create("一条短片", 15, "9:16", ["unknown"], self.root, self.cfg)

    def test_heuristic_is_marked_and_not_claimed_as_model(self):
        result, label = describe("启动，加速，腾空", 15, 3, self.cfg)
        self.assertEqual(label, "heuristic_draft_not_ai_storyboard")
        self.assertEqual(len(result), 3)

    def test_insecure_remote_model_endpoint_rejected(self):
        with self.assertRaisesRegex(ProviderError, "HTTPS"):
            endpoint({"url": "http://example.com:8188"})
        self.assertEqual(endpoint({"url": "http://localhost:8188/"}),
                         "http://localhost:8188")

    def test_job_lookup(self):
        root = self.make_job()
        self.assertEqual(job_root(root / "manifest.json"), root)
        with self.assertRaises(FlowError):
            job_root(self.root / "missing")

    def test_cost_cap(self):
        cfg = {**self.cfg, "max_shots": 1}
        with self.assertRaisesRegex(FlowError, "cost cap"):
            create("未来城市超跑视频", 35, "9:16", [], self.root, cfg)


if __name__ == "__main__":
    unittest.main()
