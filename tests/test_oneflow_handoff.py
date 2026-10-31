"""No-inference OneFlow handoff tests: source integrity, no-crop, release gates.

Synthetic source fixture only, not an AI generated video.
"""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from oneflow.handoff import HandoffError, assemble_package, digest, original_brief, plan_shots, verify_source

HAS_PIL = importlib.util.find_spec("PIL") is not None
HAS_FFMPEG = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


@unittest.skipUnless(HAS_PIL, "Pillow needed for PNG fixture and packaging")
class HandoffTests(unittest.TestCase):
    def create_source(self, root, *, provider="Cloudflare Workers AI"):
        from PIL import Image
        source = Path(root) / "upstream"
        source.mkdir()
        image = source / "S01.png"
        Image.new("RGB", (1024, 1024), (31, 42, 55)).save(image, "PNG")
        record = {
            "status": "IMAGE_GENERATED_REVIEW_REQUIRED",
            "shot_id": "S01",
            "generated_image": "S01.png",
            "provider": provider,
            "model": "@cf/black-forest-labs/flux-1-schnell",
            "sha256": digest(image),
            "actual_width": 1024,
            "actual_height": 1024,
            "prompt": "One single 9:16 photorealistic cinematic still image, intended as an "
                      "approved first frame for image-to-video. User brief: Original black "
                      "hypercar at night, blue rear jet exhaust, no narration. "
                      "One moment, stable subjects and props, physically plausible composition."
        }
        (source / "S01.json").write_text(json.dumps(record), encoding="utf-8")
        return source, record

    def test_valid_source_two_providers(self):
        for provider in ("Cloudflare Workers AI", "OVHcloud AI Endpoints (anonymous)"):
            with tempfile.TemporaryDirectory() as tmp:
                source, rec = self.create_source(tmp, provider=provider)
                self.assertEqual(verify_source(source)[1]["provider"], provider)
                self.assertIn("no narration", original_brief(rec))

    def test_integrity_check_stops_tampered_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, record = self.create_source(tmp)
            (source / "S01.png").write_bytes(b"tampered")
            with self.assertRaisesRegex(HandoffError, "SHA256"):
                verify_source(source)

    def test_spoofed_image_provider_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, record = self.create_source(tmp)
            record["provider"] = "Unverified paid source"
            (source / "S01.json").write_text(json.dumps(record))
            with self.assertRaisesRegex(HandoffError, "provider"):
                verify_source(source)

    def test_requires_real_generated_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, record = self.create_source(tmp)
            record["status"] = "DRY_RUN_NO_IMAGE_GENERATED"
            (source / "S01.json").write_text(json.dumps(record))
            with self.assertRaisesRegex(HandoffError, "successfully generated"):
                verify_source(source)

    def test_no_cropping_and_no_false_publishing_claims(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmp:
            src, record = self.create_source(tmp)
            out = Path(tmp) / "handoff"
            result = assemble_package(src, out, 1234, 35)
            self.assertEqual(result["status"], "ASSETS_READY_VIDEO_NOT_GENERATED_REVIEW_REQUIRED")
            self.assertFalse(result["readiness"]["video_generated"])
            self.assertFalse(result["readiness"]["published"])
            self.assertEqual(digest(out / "S01_original.png"), record["sha256"])
            with Image.open(out / "S01_portrait_letterbox.png") as pic:
                self.assertEqual(pic.size, (1080, 1920))
                self.assertEqual(pic.getpixel((540, 50)), (8, 10, 13))
                self.assertEqual(pic.getpixel((540, 960)), (31, 42, 55))
            doc = json.loads((out / "handoff.json").read_text())
            self.assertEqual(len(doc["shots"]), 7)
            self.assertEqual(sum(shot["seconds"] for shot in doc["shots"]), 35)
            self.assertEqual(doc["model_video_requests"], 0)
            self.assertEqual(doc["publisher_requests"], 0)
            self.assertEqual(doc["shots"][0]["status"], "KEYFRAME_EXISTS_REVIEW_REQUIRED")
            self.assertEqual(doc["shots"][1]["status"], "SHOT_PLANNED_NO_IMAGE")
            self.assertEqual(len(json.loads((out / "publication_drafts.json").read_text())["profiles"]), 6)
            self.assertIn("STILL", (out / "README.txt").read_text())
            self.assertTrue((out / "wan_s01_prompt.txt").is_file())

    def test_output_rejects_duplicate_without_overwriting(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, _ = self.create_source(tmp)
            out = Path(tmp) / "handoff"
            assemble_package(src, out, 1234, 15)
            with self.assertRaisesRegex(HandoffError, "empty"):
                assemble_package(src, out, 1234, 15)

    def test_rejects_unapproved_duration_and_run_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, _ = self.create_source(tmp)
            with self.assertRaisesRegex(HandoffError, "Allowed"):
                assemble_package(src, Path(tmp) / "out", 1234, 90)
            with self.assertRaisesRegex(HandoffError, "positive"):
                assemble_package(src, Path(tmp) / "out", 0, 5)

    @unittest.skipUnless(HAS_FFMPEG, "FFmpeg needed for static preview check")
    def test_static_preview_explicitly_not_model_video(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, _ = self.create_source(tmp)
            out = Path(tmp) / "handoff"
            result = assemble_package(src, out, 1234, 5, preview=True)
            prev = result["outputs"]["static_preview"]
            self.assertEqual(prev["label"], "STATIC_STILL_NO_AI_MOTION")
            self.assertEqual(prev["duration_seconds"], 5)
            self.assertTrue((out / prev["file"]).is_file())
            self.assertFalse(result["readiness"]["video_generated"])


class ShotPlanningTests(unittest.TestCase):
    def test_count_capped_and_film_prompt_modules(self):
        shots = plan_shots("One black hypercar, jet exhaust starts only after opening", 35)
        self.assertEqual(len(shots), 7)
        self.assertIn("1. Original image/asset lock", shots[0]["seven_module_prompt"])
        self.assertIn("7. Negative constraints", shots[0]["seven_module_prompt"])
        self.assertEqual(shots[0]["audio_cue"]["status"], "CUE_ONLY_NO_AUDIO_FILE")
        with self.assertRaisesRegex(HandoffError, "1-12"):
            plan_shots("anything", 90)


if __name__ == "__main__":
    unittest.main()
