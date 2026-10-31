"""Offline tests for fal.ai adapter: no real provider or billing calls."""
import argparse
from io import BytesIO
from pathlib import Path
import tempfile
import unittest

from PIL import Image
from oneflow.fal_image import (
    FAL_MODEL, download_fal_image, estimate_usd, execute,
)
from oneflow.image_generation import ImageFlowError


def makeargs(tmp, **kw):
    data = {
        "brief": "A cinematic photorealistic black racing car on a rainy track",
        "request_file": None, "shot": "S01", "seed": 42,
        "width": 768, "height": 1344,
        "output": str(Path(tmp) / "generated-images"),
        "dry_run": False, "approve_one_image": False,
    }
    data.update(kw)
    return argparse.Namespace(**data)


def sample_png():
    out = BytesIO()
    Image.new("RGB", (768, 1344), (12, 43, 88)).save(out, "PNG")
    return out.getvalue()


class FalImageTests(unittest.TestCase):
    def test_estimated_billing_rounds_up_megapixels(self):
        self.assertEqual(estimate_usd(768, 1344), 0.006)
        self.assertEqual(estimate_usd(512, 512), 0.003)

    def test_dry_run_no_secret_no_charge(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = execute(makeargs(tmp, dry_run=True))
            self.assertEqual(data["provider"], "fal.ai")
            self.assertEqual(data["model"], "FLUX.1-schnell")
            self.assertEqual(data["status"], "DRY_RUN_NO_IMAGE_GENERATED")
            self.assertFalse(Path(tmp, "generated-images").exists())

    def test_charge_blocked_before_explicit_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ImageFlowError, "explicitly authorized"):
                execute(makeargs(tmp), token="fal_dummy")
            self.assertFalse(Path(tmp, "generated-images").exists())

    def test_missing_key_does_not_call_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ImageFlowError, "MISSING_FAL_KEY"):
                execute(makeargs(tmp, approve_one_image=True), token="")

    def test_mock_image_creates_real_png_and_report(self):
        calls = []
        def fake_submit(model, arguments):
            calls.append((model, arguments))
            return {
                "images": [{"url": "https://v3.fal.media/files/demo.png"}],
                "has_nsfw_concepts": [False],
            }
        with tempfile.TemporaryDirectory() as tmp:
            result = execute(makeargs(tmp, approve_one_image=True), token="dummy",
                             submit=fake_submit, download=lambda url: sample_png())
            self.assertEqual(result["status"], "IMAGE_GENERATED_REVIEW_REQUIRED")
            self.assertEqual(result["provider_endpoint"], FAL_MODEL)
            self.assertEqual(result["actual_width"], 768)
            self.assertEqual(len(result["sha256"]), 64)
            self.assertTrue(Path(tmp, "generated-images", "S01.json").exists())
            with Image.open(Path(tmp, "generated-images", "S01.png")) as img:
                self.assertEqual(img.size, (768, 1344))
                self.assertEqual(img.format, "PNG")
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0][0], FAL_MODEL)
            self.assertEqual(calls[0][1]["num_images"], 1)
            self.assertTrue(calls[0][1]["enable_safety_checker"])

    def test_failed_response_creates_no_claimed_image(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ImageFlowError, "exactly one"):
                execute(makeargs(tmp, approve_one_image=True), token="dummy",
                        submit=lambda *a, **kw: {"images": []})
            self.assertFalse(Path(tmp, "generated-images", "S01.png").exists())

    def test_existing_output_prevents_duplicate_paid_request(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp, "generated-images")
            dest.mkdir()
            (dest / "S01.png").write_bytes(b"original")
            with self.assertRaisesRegex(ImageFlowError, "double billing"):
                execute(makeargs(tmp, approve_one_image=True), token="dummy",
                        submit=lambda *a, **kw: self.fail("must not call provider"))
            self.assertEqual((dest / "S01.png").read_bytes(), b"original")

    def test_output_download_refuses_non_provider_urls(self):
        with self.assertRaisesRegex(ImageFlowError, "Unexpected image output host"):
            download_fal_image("http://localhost:5000/secret")
        with self.assertRaisesRegex(ImageFlowError, "Unexpected image output host"):
            download_fal_image("https://evil.example/secret")

    def test_image_bytes_must_decode(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ImageFlowError, "cannot be decoded"):
                execute(makeargs(tmp, approve_one_image=True), token="dummy",
                        submit=lambda *a, **kw: {"images": [{"url": "https://v3.fal.media/test"}]},
                        download=lambda url: b"notimage" * 100)
            self.assertFalse(Path(tmp, "generated-images", "S01.png").exists())


if __name__ == "__main__":
    unittest.main()
