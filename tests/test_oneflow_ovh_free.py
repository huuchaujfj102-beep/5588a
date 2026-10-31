"""Safe tests for OVHcloud free text-to-image adapter. Never contact cloud in tests."""
import argparse
from io import BytesIO
import importlib.util
from pathlib import Path
import tempfile
import unittest
from urllib.error import HTTPError

from oneflow.image_generation import ImageFlowError
from oneflow.ovh_free_image import (
    ENDPOINT, MAX_IMAGE_BYTES, execute, fetch_image_once,
)

HAS_PIL = importlib.util.find_spec("PIL") is not None


def args(out, **updates):
    params = dict(
        brief="Photorealistic single futuristic black hypercar on wet nighttime track",
        shot="S01", seed=6, output=str(out),
        dry_run=False, approve_free_test=False,
    )
    params.update(updates)
    return argparse.Namespace(**params)


class MockResponse:
    def __init__(self, value):
        self.value = value
    def __enter__(self):
        return self
    def __exit__(self, *exc):
        return False
    def read(self, size):
        return self.value[:size]


class OVHFreeTests(unittest.TestCase):
    def test_dry_run_does_not_call_cloud(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = execute(args(Path(tmp), dry_run=True),
                             transport=lambda *a, **kw: self.fail("Cloud called in dry-run"))
            self.assertEqual(result["status"], "DRY_RUN_NO_IMAGE_GENERATED")
            self.assertFalse(Path(tmp, "S01.png").exists())

    def test_explicit_opt_in_before_inference(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ImageFlowError, "Explicit free-test approval"):
                execute(args(Path(tmp)),
                        transport=lambda *a, **kw: self.fail("Cloud called without opt-in"))

    def test_anonymous_single_post_no_authorization_header(self):
        calls = []
        def fake(req, timeout):
            calls.append((req, timeout))
            return MockResponse(b"a" * 500)
        self.assertEqual(len(fetch_image_once("cinematic black supercar", opener=fake)), 500)
        self.assertEqual(len(calls), 1)
        req, timeout = calls[0]
        self.assertEqual(req.full_url, ENDPOINT)
        self.assertEqual(req.get_method(), "POST")
        self.assertNotIn("authorization", {x.lower() for x in req.headers})
        self.assertIn(b"cinematic black supercar", req.data)

    def test_http_429_stops_without_retry(self):
        calls = []
        def rate_limited(req, timeout):
            calls.append(1)
            raise HTTPError(req.full_url, 429, "Too Many", {}, None)
        with self.assertRaisesRegex(ImageFlowError, "HTTP_429"):
            fetch_image_once("cinematic original car", opener=rate_limited)
        self.assertEqual(len(calls), 1)

    def test_invalid_brief_prevents_network(self):
        with self.assertRaises(ImageFlowError):
            fetch_image_once("bad", opener=lambda *a, **kw: self.fail("called"))

    def test_oversized_response_rejected(self):
        with self.assertRaisesRegex(ImageFlowError, "exceeds maximum"):
            fetch_image_once("cinematic black supercar",
                             opener=lambda *a, **kw: MockResponse(b"x" * (MAX_IMAGE_BYTES + 1)))

    @unittest.skipUnless(HAS_PIL, "Pillow required for binary image fixtures")
    def test_decodable_png_and_sha_report(self):
        from PIL import Image
        source = BytesIO()
        Image.new("RGB", (1024, 1024), (17, 32, 63)).save(source, format="JPEG")
        invoked = []
        def fake(req, timeout):
            invoked.append(1)
            return MockResponse(source.getvalue())
        with tempfile.TemporaryDirectory() as tmp:
            result = execute(args(Path(tmp), approve_free_test=True), transport=fake)
            self.assertEqual(result["status"], "IMAGE_GENERATED_REVIEW_REQUIRED")
            self.assertEqual(result["actual_width"], 1024)
            self.assertEqual(result["actual_height"], 1024)
            self.assertEqual(result["request_count"], 1)
            self.assertEqual(len(result["sha256"]), 64)
            self.assertTrue(Path(tmp, "S01.png").exists())
            self.assertTrue(Path(tmp, "S01.json").exists())
        self.assertEqual(len(invoked), 1)

    @unittest.skipUnless(HAS_PIL, "Pillow required for binary image fixtures")
    def test_reject_non_image_and_never_fabricate(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ImageFlowError, "decodable"):
                execute(args(Path(tmp), approve_free_test=True),
                        transport=lambda *a, **kw: MockResponse(b"bad data" * 250))
            self.assertFalse(Path(tmp, "S01.png").exists())
            self.assertFalse(Path(tmp, "S01.json").exists())


if __name__ == "__main__":
    unittest.main()
