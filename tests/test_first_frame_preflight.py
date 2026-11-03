"""No network or paid API calls: strict public image preflight tests."""
import io
import unittest
import urllib.error
from unittest.mock import patch

from oneflow.core import FlowError
from oneflow.first_frame_preflight import verify_public_image


class FakeImage(io.BytesIO):
    def __init__(self, data, mime="image/jpeg"):
        super().__init__(data)
        self.headers = {"Content-Type": mime}
    def __enter__(self):
        return self
    def __exit__(self, *args):
        self.close()


class ReferencePreflightTests(unittest.TestCase):
    def test_valid_jpeg_is_read_only(self):
        calls = []
        def open_image(req, timeout):
            calls.append(req.get_method())
            self.assertEqual(timeout, 25)
            return FakeImage(bytes.fromhex("ffd8ff") + b"fakecontent" * 30)
        with patch("oneflow.first_frame_preflight._checked_public_url",
                   return_value="https://example.com/car.jpg"):
            result = verify_public_image("https://example.com/car.jpg", transport=open_image)
        self.assertTrue(result["verified_public_image"])
        self.assertFalse(result["paid_task_created"])
        self.assertEqual(calls, ["GET"])

    def test_html_fake_image_fails_before_video(self):
        with patch("oneflow.first_frame_preflight._checked_public_url",
                   return_value="https://example.com/unknown.jpg"):
            with self.assertRaisesRegex(FlowError, "FORMAT_INVALID"):
                verify_public_image("https://example.com/unknown.jpg",
                                    transport=lambda req, timeout: FakeImage(b"<html>" * 50, "text/html"))

    def test_unavailable_file_fails_without_paid_submission(self):
        def missing(req, timeout):
            raise urllib.error.HTTPError(req.full_url, 404, "No", {}, None)
        with patch("oneflow.first_frame_preflight._checked_public_url",
                   return_value="https://example.com/404.jpg"):
            with self.assertRaisesRegex(FlowError, "UNREACHABLE"):
                verify_public_image("https://example.com/404.jpg", transport=missing)

    def test_signed_url_rejected_before_transport(self):
        with patch("oneflow.first_frame_preflight._checked_public_url",
                   return_value="https://example.com/car.jpg?sig=private"):
            with self.assertRaisesRegex(FlowError, "no signed query"):
                verify_public_image("https://example.com/car.jpg",
                                    transport=lambda *args: self.fail("network contacted"))


if __name__ == "__main__":
    unittest.main()
