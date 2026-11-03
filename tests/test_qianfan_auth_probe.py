"""Only mocked GETs. These tests never contact or bill Baidu."""
import io
import os
import urllib.error
import unittest
from unittest.mock import patch

from oneflow.qianfan_auth_probe import probe_vq_auth
from oneflow.qianfan_media import MediaTaskError


class DummyResponse(io.BytesIO):
    status = 200
    def __enter__(self):
        return self
    def __exit__(self, *args):
        self.close()


class AuthPreflightTests(unittest.TestCase):
    def test_auth_401_rejected_before_paid(self):
        verbs = []
        def fake(req, timeout):
            verbs.append(req.get_method())
            raise urllib.error.HTTPError(req.full_url, 401, "no", {}, None)
        with patch.dict(os.environ, {"QIANFAN_API_KEY": "bce-v3/ALTAK-TEST/test"}):
            with self.assertRaisesRegex(MediaTaskError, "HTTP 401"):
                probe_vq_auth(transport=fake)
        self.assertEqual(verbs, ["GET"])

    def test_auth_403_rejected_before_paid(self):
        with patch.dict(os.environ, {"QIANFAN_API_KEY": "bce-v3/ALTAK-TEST/test"}):
            with self.assertRaisesRegex(MediaTaskError, "HTTP 403"):
                probe_vq_auth(transport=lambda req, timeout: (
                    (_ for _ in ()).throw(
                        urllib.error.HTTPError(req.full_url, 403, "denied", {}, None))))

    def test_missing_and_header_prefix_rejected_without_transport(self):
        for value in ("", "Bearer bce-v3/ALTAK-TEST/test", "bce-v3/ALTAK-TEST/test\n"):
            with self.subTest(key=value):
                with patch.dict(os.environ, {"QIANFAN_API_KEY": value}):
                    with patch("urllib.request.build_opener") as opener:
                        with self.assertRaises(MediaTaskError):
                            probe_vq_auth()
                        opener.assert_not_called()

    def test_404_only_means_endpoint_reached(self):
        seen = []
        def fake(req, timeout):
            seen.append(req)
            raise urllib.error.HTTPError(req.full_url, 404, "missing task", {}, None)
        with patch.dict(os.environ, {"QIANFAN_API_KEY": "bce-v3/ALTAK-TEST/test"}):
            out = probe_vq_auth(transport=fake)
        self.assertEqual(out["authorization"], "endpoint_reached_not_model_entitlement")
        self.assertFalse(out["created_task"])
        self.assertEqual(seen[0].get_method(), "GET")
        self.assertEqual(seen[0].data, None)

    def test_200_only_establishes_endpoint_reachability(self):
        with patch.dict(os.environ, {"QIANFAN_API_KEY": "bce-v3/ALTAK-TEST/test"}):
            out = probe_vq_auth(transport=lambda req, timeout: DummyResponse(b"{}"))
        self.assertEqual(out["http_status"], 200)
        self.assertEqual(out["authorization"], "endpoint_reached_not_model_entitlement")


if __name__ == "__main__":
    unittest.main()
