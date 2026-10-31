"""Validate one-sentence image generation, billing gates and real image bytes.

A mocked HF client exercises the provider adapter without claiming cloud inference.
"""
import argparse
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from oneflow.image_generation import (
    ImageFlowError, MODEL, build_plan, build_prompt, execute, prompt_from_request,
)


def makeargs(tmp, **patch):
    data = dict(brief="Snow White cinematic mirror scene",
                request_file=None, shot="S01", seed=128839,
                width=768, height=1344, output=str(Path(tmp) / "output"),
                dry_run=False, approve_one_image=False)
    data.update(patch)
    return argparse.Namespace(**data)


class ImageFlowTests(unittest.TestCase):
    def test_one_sentence_to_audited_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = execute(makeargs(tmp, dry_run=True))
        self.assertEqual(report["status"], "DRY_RUN_NO_IMAGE_GENERATED")
        self.assertIsNone(report["generated_image"])
        self.assertIn("Snow White", report["prompt"])
        self.assertEqual(report["model"], MODEL)

    def test_real_billing_without_approval_fails_even_if_token_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ImageFlowError, "explicitly authorized"):
                execute(makeargs(tmp), token="hf_test_unused")
            self.assertFalse((Path(tmp) / "output").exists())

    def test_missing_secret_fails_not_false_positive(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ImageFlowError, "MISSING_HF_TOKEN"):
                execute(makeargs(tmp, approve_one_image=True), token="")
            self.assertFalse((Path(tmp) / "output").exists())

    def test_invalid_shot_and_size_fail(self):
        with self.assertRaises(ImageFlowError):
            build_plan("prompt", "S99", 1, 768, 1344)
        with self.assertRaises(ImageFlowError):
            build_plan("prompt", "S01", 1, 8192, 8192)

    def test_story_request_fixes_exact_character_appearance(self):
        request = "oneflow/requests/snow-white-seven-dwarfs-60s.json"
        if not Path(request).exists():
            self.skipTest("Repository sample request missing")
        brief = prompt_from_request(request, "S01")
        self.assertIn("王后", brief)
        self.assertIn("魔镜", brief)
        self.assertIn("7. NEGATIVE:", brief)
        self.assertNotIn("石砾: ", brief)
        self.assertNotIn("星砂: ", brief)

    def test_existing_file_fails_before_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "output"
            output.mkdir()
            (output / "S01.png").write_bytes(b"existing previous user image")
            with self.assertRaisesRegex(ImageFlowError, "double billing"):
                execute(makeargs(tmp, approve_one_image=True),
                        token="hf_dummy")
            self.assertEqual((output / "S01.png").read_bytes(), b"existing previous user image")


@unittest.skipUnless(importlib.util.find_spec("PIL"), "Pillow not installed in this CI")
class ImageByteIntegrationTests(unittest.TestCase):
    def test_mock_client_returns_real_decodeable_png_and_provenance(self):
        from PIL import Image

        class FakeHF:
            calls = []
            def __init__(self, provider, api_key):
                self.asserted = provider == "auto" and api_key == "hf_test"
                if not self.asserted:
                    raise AssertionError("Unexpected provider or secret")
            def text_to_image(self, **kwargs):
                FakeHF.calls.append(kwargs)
                return Image.new("RGB", (768, 1344), (33, 52, 70))
        with tempfile.TemporaryDirectory() as tmp:
            report = execute(makeargs(tmp, approve_one_image=True),
                             token="hf_test", client_cls=FakeHF)
            png = Path(tmp) / "output" / "S01.png"
            self.assertTrue(png.is_file())
            with Image.open(png) as img:
                self.assertEqual(img.size, (768, 1344))
                self.assertEqual(img.format, "PNG")
            self.assertEqual(report["status"], "IMAGE_GENERATED_REVIEW_REQUIRED")
            self.assertEqual(len(report["sha256"]), 64)
            self.assertEqual(FakeHF.calls[-1]["model"], MODEL)
            self.assertEqual(FakeHF.calls[-1]["num_inference_steps"], 4)
            self.assertEqual(json.loads((png.parent / "S01.json").read_text())["sha256"], report["sha256"])

    def test_wrong_object_rejected_not_saved_as_image(self):
        class FakeBadHF:
            def __init__(self, **kwargs):
                pass
            def text_to_image(self, **kwargs):
                return {"error": "not an image"}
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ImageFlowError, "decodable image"):
                execute(makeargs(tmp, approve_one_image=True),
                        token="hf_test", client_cls=FakeBadHF)
            self.assertFalse((Path(tmp) / "output" / "S01.png").exists())


if __name__ == "__main__":
    unittest.main()
