import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from oneflow.router import RoutingError, catalog, route, preflight
from oneflow.director import film_prompt
from oneflow.visual_review import validate_review, VisualReviewError
from oneflow.core import describe, normalize


class EnhancedFlowTests(unittest.TestCase):
    def candidate(self, model, priority=100, license_checked=False):
        return {"kind": "comfyui", "model_id": model, "priority": priority,
                "license_checked": license_checked,
                "graph": "private-inputs/workflows/example-api.json",
                "patches": [{"node": "6", "input": "text", "from": "prompt"}]}

    def test_model_catalog_explains_limits(self):
        models = catalog()
        self.assertIn("ltx2", models)
        self.assertIn("qwen3-vl", models)
        self.assertIn("wan2.2-ti2v-5b", models)
        self.assertEqual(models["mmaudio"]["license_policy"], "noncommercial")

    def test_noncommercial_checkpoint_blocked_in_commercial_project(self):
        with self.assertRaisesRegex(RoutingError, "Noncommercial"):
            route("audio", [self.candidate("mmaudio")], commercial=True)

    def test_noncommercial_checkpoint_still_needs_valid_graph(self):
        self.assertEqual(route("audio", [self.candidate("mmaudio")], commercial=False)[0]["model_id"],
                         "mmaudio")

    def test_ltx_license_must_be_checked(self):
        with self.assertRaisesRegex(RoutingError, "license approval"):
            route("video", [self.candidate("ltx2")])
        ok = route("video", [self.candidate("ltx2", license_checked=True)])
        self.assertEqual(ok[0]["model_id"], "ltx2")

    def test_unknown_model_cannot_sneak_into_routing(self):
        with self.assertRaisesRegex(RoutingError, "unknown"):
            route("image", [self.candidate("unregistered")])

    def test_ranked_router_is_stable(self):
        providers = [self.candidate("wan2.2-ti2v-5b", 30, True),
                     self.candidate("ltx2", 10, True)]
        self.assertEqual([x["model_id"] for x in route("video", providers)],
                         ["ltx2", "wan2.2-ti2v-5b"])

    def test_embedded_av_preflight_requires_verified_provider(self):
        cfg = {"video": [self.candidate("ltx2", license_checked=True)],
               "audio_mode": "embedded"}
        with self.assertRaisesRegex(RoutingError, "verified as AV"):
            preflight(cfg)
        cfg["video"][0]["supports_embedded_audio"] = True
        self.assertTrue(preflight(cfg))

    def test_frame_bridge_needs_reference_mapping(self):
        cfg = {"image": [self.candidate("flux2-klein-4b")],
               "video": [self.candidate("ltx2", license_checked=True)],
               "frame_bridge": True}
        with self.assertRaisesRegex(RoutingError, "Frame bridge"):
            preflight(cfg)
        cfg["image"][0]["patches"].append({"node": "15", "input": "image",
                                           "from": "reference_image_upload"})
        self.assertTrue(preflight(cfg))

    def test_director_has_strict_seven_modules_and_prior_phase(self):
        content = film_prompt("轰鸣，加速，腾空，尾焰，飞远", "腾空", "加速", 3, 5)
        for number in range(1, 8):
            self.assertIn(str(number) + ".", content)
        self.assertIn("Prior narrative phase: 加速", content)
        self.assertIn("unapproved new actors", content)

    def test_story_order_preserved_with_longer_shot_count(self):
        shots, kind = describe("启动，加速，腾空，尾焰，飞远", 35, 7,
                               {"story": {"kind": "heuristic"}})
        self.assertEqual(kind, "heuristic_draft_not_ai_storyboard")
        phases = [s["phase"] for s in shots]
        self.assertEqual(phases[0], "启动")
        self.assertEqual(phases[-1], "飞远")
        self.assertLess(phases.index("加速"), phases.index("腾空"))
        self.assertLess(phases.index("腾空"), phases.index("尾焰"))

    def test_vlm_warnings_are_advisory_not_auto_approval(self):
        valid = {"findings": [{"severity": "warning", "description": "Camera-side ambiguity"}],
                 "uncertainties": ["Two frames cannot prove motion physics"]}
        self.assertEqual(validate_review(valid), valid)
        with self.assertRaises(VisualReviewError):
            validate_review({"findings": [{"severity": "PASS", "description": "all good"}],
                             "uncertainties": []})

    def test_normalizer_prefers_real_embedded_av_over_silent_track(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "media").mkdir()
            shot = {"id": "S01", "video": "media/clip.mp4", "audio": None, "seconds": 5}
            probe_output = {
                "format": {"duration": "5.2"},
                "streams": [{"codec_type": "video"}, {"codec_type": "audio"}]
            }
            called = []
            with patch("oneflow.core.probe", return_value=probe_output), \
                 patch("oneflow.core.command", side_effect=lambda c, **k: called.append(c)):
                normalize(root, shot, 24, 1080, 1920, True)
            self.assertIn("0:a:0", called[0])
            self.assertNotIn("anullsrc=r=48000:cl=stereo", called[0])


if __name__ == "__main__":
    unittest.main()
