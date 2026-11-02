"""Mock-only Douyin official upload/create tests. No OAuth network call."""
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from oneflow.core import (
    FlowError, config, create, digest, load_json, save_json,
)
from oneflow.douyin_publisher import publish_approved_douyin, UPLOAD_URL, CREATE_URL


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self
    def __exit__(self, *exc):
        self.close()


def result(value):
    return FakeResponse(json.dumps(value).encode("utf8"))


class DouyinPublisherTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.job = create("一辆原创概念超跑加速疾驰", 5, "9:16",
                          ["douyin"], self.root, config())
        self.clip = self.job / "final-draft.mp4"
        self.clip.write_bytes(b"\x00\x00\x00\x18ftypisom" + b"x" * 1024)
        m = load_json(self.job / "manifest.json")
        m["render"] = "final-draft.mp4"
        m["status"] = "APPROVED"
        m["approval"] = {"reviewer": "real-editor-test", "video_sha256": digest(self.clip)}
        save_json(self.job / "manifest.json", m)
        save_json(self.job / "qc.json", {"video_sha256": digest(self.clip)})

    def test_never_uploads_without_explicit_consent(self):
        with patch.dict(os.environ, {"DOUYIN_ACCESS_TOKEN": "fake",
                                     "DOUYIN_OPEN_ID": "fake"}):
            with patch("urllib.request.urlopen") as call:
                with self.assertRaisesRegex(FlowError, "Explicit per-platform"):
                    publish_approved_douyin(self.job, consent=False)
                call.assert_not_called()

    def test_no_token_no_upload(self):
        with patch.dict(os.environ, {"DOUYIN_ACCESS_TOKEN": "",
                                     "DOUYIN_OPEN_ID": ""}):
            with patch("urllib.request.urlopen") as call:
                with self.assertRaisesRegex(FlowError, "access token"):
                    publish_approved_douyin(self.job, consent=True)
                call.assert_not_called()

    def test_gate_blocks_unapproved_or_mutated_video(self):
        self.clip.write_bytes(self.clip.read_bytes() + b"x")
        with patch.dict(os.environ, {"DOUYIN_ACCESS_TOKEN": "fake",
                                     "DOUYIN_OPEN_ID": "fake"}):
            with patch("urllib.request.urlopen") as call:
                with self.assertRaisesRegex(FlowError, "changed since approval"):
                    publish_approved_douyin(self.job, consent=True)
                call.assert_not_called()

    def test_authenticated_private_upload_create_only_once(self):
        calls = []
        def mock(req, timeout):
            calls.append(req)
            if req.full_url.startswith(UPLOAD_URL):
                return result({"data": {
                    "video": {"video_id": "video-encrypted"}, "error_code": 0},
                    "extra": {"error_code": 0}})
            if req.full_url.startswith(CREATE_URL):
                payload = json.loads(req.data)
                self.assertEqual(payload["video_id"], "video-encrypted")
                self.assertEqual(payload["private_status"], 1)
                return result({"data": {
                    "item_id": "douyin-private-item", "error_code": 0},
                    "extra": {"error_code": 0}})
            raise RuntimeError("wrong URL")
        with patch.dict(os.environ, {"DOUYIN_ACCESS_TOKEN": "fake-token",
                                     "DOUYIN_OPEN_ID": "fake-openid"}):
            record = publish_approved_douyin(self.job, consent=True, transport=mock)
            record2 = publish_approved_douyin(self.job, consent=True, transport=mock)
        self.assertEqual(len(calls), 2)
        self.assertEqual(record["status"], "pending")
        self.assertEqual(record2["item_id"], "douyin-private-item")
        self.assertTrue(all(req.get_header("Access-token") == "fake-token" for req in calls))
        manifest = load_json(self.job / "manifest.json")
        self.assertEqual(manifest["publication"]["douyin"]["status"], "pending")
        self.assertIsNone(manifest["publication"]["douyin"]["url"])
        self.assertEqual(manifest["status"], "APPROVED")

    def test_upload_unknown_refuses_second_attempt(self):
        calls = []
        def mock(req, timeout):
            calls.append(req)
            raise RuntimeError("unknown provider")
        with patch.dict(os.environ, {"DOUYIN_ACCESS_TOKEN": "fake",
                                     "DOUYIN_OPEN_ID": "fake"}):
            with self.assertRaises(FlowError):
                publish_approved_douyin(self.job, consent=True, transport=mock)
            with self.assertRaisesRegex(FlowError, "uncertain"):
                publish_approved_douyin(self.job, consent=True, transport=mock)
        self.assertEqual(len(calls), 1)


    def test_public_post_requires_separate_explicit_confirmation(self):
        with patch.dict(os.environ, {"DOUYIN_ACCESS_TOKEN": "fake",
                                     "DOUYIN_OPEN_ID": "fake"}):
            with patch("urllib.request.urlopen") as call:
                with self.assertRaisesRegex(FlowError, "confirm-public"):
                    publish_approved_douyin(self.job, consent=True,
                                            visibility="public", confirm_public=False)
                call.assert_not_called()

    def test_public_post_uses_explicit_visibility_zero_but_still_pending(self):
        uploaded = []
        def mock(req, timeout):
            uploaded.append(req)
            if req.full_url.startswith(UPLOAD_URL):
                return result({"data": {"video": {"video_id": "enc-vid"},
                                        "error_code": 0},
                               "extra": {"error_code": 0}})
            payload = json.loads(req.data)
            self.assertEqual(payload["private_status"], 0)
            return result({"data": {"item_id": "pending-review", "error_code": 0},
                           "extra": {"error_code": 0}})
        with patch.dict(os.environ, {"DOUYIN_ACCESS_TOKEN": "fake",
                                     "DOUYIN_OPEN_ID": "fake"}):
            out = publish_approved_douyin(self.job, consent=True,
                   visibility="public", confirm_public=True, transport=mock)
        self.assertEqual(out["status"], "pending")
        self.assertEqual(len(uploaded), 2)
        data = load_json(self.job / "manifest.json")
        self.assertEqual(data["douyin_direct"]["requested_visibility"], "public")
        self.assertIsNone(data["publication"]["douyin"]["url"])



if __name__ == "__main__":
    unittest.main()
