"""Offline tests for Cloudflare Workers AI FLUX.1 Schnell. No external calls."""
import argparse
import base64
from io import BytesIO
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from urllib.error import HTTPError

from oneflow.cloudflare_free_image import (
    MODEL, ENDPOINT_ROOT, infer_once, execute, parse_image_response,
)
from oneflow.image_generation import ImageFlowError

HAS_PIL = importlib.util.find_spec("PIL") is not None


def makeargs(path, **overrides):
    data = dict(
        brief="Photorealistic carbon fiber futuristic hypercar in rain at night",
        shot="S01", seed=25, steps=4, output=str(path),
        dry_run=False, approve_free_test=False, confirm_workers_free=False,
    )
    data.update(overrides)
    return argparse.Namespace(**data)


def envelope(image):
    return json.dumps({
        "success": True,
        "result": {"image": base64.b64encode(image).decode("ascii")},
        "errors": [],
    }).encode("utf-8")


class FakeResponse:
    def __init__(self, raw):
        self.raw = raw
    def __enter__(self):
        return self
    def __exit__(self, *exc):
        return False
    def read(self, limit):
        return self.raw[:limit]


class CloudflareFreeImageTests(unittest.TestCase):
    account = "b" * 32

    def test_dry_run_needs_no_credentials_and_never_calls_provider(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = execute(makeargs(Path(tmp), dry_run=True),
                             opener=lambda *a, **k: self.fail("network used in dry run"))
            self.assertEqual(report["status"], "DRY_RUN_NO_IMAGE_GENERATED")
            self.assertEqual(report["provider"], "Cloudflare Workers AI")
            self.assertEqual(report["model"], MODEL)
            self.assertEqual(report["api_calls"], 0)
            self.assertFalse(Path(tmp, "S01.png").exists())

    def test_requires_both_free_plan_and_one_time_consent(self):
        with tempfile.TemporaryDirectory() as tmp:
            for approvals in [
                {"approve_free_test": False, "confirm_workers_free": True},
                {"approve_free_test": True, "confirm_workers_free": False},
            ]:
                with self.assertRaisesRegex(ImageFlowError, "Manual approval"):
                    execute(makeargs(Path(tmp), **approvals),
                            account_id=self.account, token="test",
                            opener=lambda *a, **k: self.fail("network used"))

    def test_needs_exact_account_id_and_token(self):
        with self.assertRaisesRegex(ImageFlowError, "ACCOUNT_ID"):
            infer_once("One original car at the racetrack", "bad", "token")
        with self.assertRaisesRegex(ImageFlowError, "API_TOKEN"):
            infer_once("One original car at the racetrack", self.account, "")

    def test_malformed_model_envelope_rejected(self):
        for raw in [b"NOT JSON", b"{}", b'{"success":false,"result":{"image":"AA=="}}',
                    b'{"success":true,"result":{}}',
                    b'{"success":true,"result":{"image":"%%%"}}']:
            with self.assertRaises(ImageFlowError):
                parse_image_response(raw)

    def test_exactly_one_authenticated_request_uses_official_model(self):
        calls = []
        def opener(request, timeout):
            calls.append((request, timeout))
            return FakeResponse(envelope(b"x" * 1000))
        raw = infer_once("Photorealistic black supercar on wet track",
                         self.account, "secret_test_token", seed=101, opener=opener)
        self.assertEqual(len(raw), 1000)
        self.assertEqual(len(calls), 1)
        request, timeout = calls[0]
        self.assertEqual(request.full_url, ENDPOINT_ROOT + "/" + self.account + "/ai/run/" + MODEL)
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.get_header("Authorization"), "Bearer secret_test_token")
        body = json.loads(request.data)
        self.assertEqual(set(body), {"prompt", "steps", "seed"})
        self.assertEqual(body["steps"], 4)

    def test_only_four_steps_no_auto_retry_for_quota_error(self):
        calls = []
        def blocked(request, timeout):
            calls.append(1)
            raise HTTPError(request.full_url, 429, "quota", {}, None)
        with self.assertRaisesRegex(ImageFlowError, "429"):
            infer_once("Photorealistic racing car in cinematic light",
                       self.account, "secret", opener=blocked)
        self.assertEqual(len(calls), 1)
        with self.assertRaisesRegex(ImageFlowError, "requires 1-4"):
            infer_once("Photorealistic racing car in cinematic light",
                       self.account, "secret", steps=8, opener=blocked)
        self.assertEqual(len(calls), 1)

    @unittest.skipUnless(HAS_PIL, "Pillow needed for image fixtures")
    def test_real_png_bytes_and_sha_from_mock_cloudflare(self):
        from PIL import Image
        jpeg = BytesIO()
        Image.new("RGB", (1024, 1024), (18, 28, 46)).save(jpeg, "JPEG")
        calls = []
        def opener(request, timeout):
            calls.append(1)
            return FakeResponse(envelope(jpeg.getvalue()))
        with tempfile.TemporaryDirectory() as tmp:
            report = execute(makeargs(Path(tmp), approve_free_test=True,
                                      confirm_workers_free=True),
                             account_id=self.account, token="test", opener=opener)
            self.assertEqual(report["status"], "IMAGE_GENERATED_REVIEW_REQUIRED")
            self.assertEqual(report["api_calls"], 1)
            self.assertEqual((report["actual_width"], report["actual_height"]), (1024, 1024))
            self.assertEqual(len(report["sha256"]), 64)
            self.assertTrue(Path(tmp, "S01.png").exists())
            self.assertTrue(Path(tmp, "S01.json").exists())
        self.assertEqual(len(calls), 1)

    @unittest.skipUnless(HAS_PIL, "Pillow needed for image fixtures")
    def test_invalid_jpeg_not_claimed_to_be_generated(self):
        def opener(request, timeout):
            return FakeResponse(envelope(b"corrupt" * 100))
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ImageFlowError, "decode/validation"):
                execute(makeargs(Path(tmp), approve_free_test=True,
                                 confirm_workers_free=True),
                        account_id=self.account, token="test", opener=opener)
            self.assertFalse(Path(tmp, "S01.png").exists())
            self.assertFalse(Path(tmp, "S01.json").exists())


if __name__ == "__main__":
    unittest.main()
