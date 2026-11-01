import json
import os
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from oneflow import magic_hour_trial as m


class MagicHourTrialTests(unittest.TestCase):
    def test_preview_is_not_marked_rendered_or_licensed(self):
        p = m.plan()
        self.assertEqual(p["duration_seconds"], 14)
        self.assertEqual(p["model"], "ltx-2.5")
        self.assertEqual(p["status"], "PREPARED_NOT_AUTHORIZED_NOT_RENDERED")
        self.assertIn("NONCOMMERCIAL", p["license_gate"])
        self.assertIn("EXACT ORIGINAL", p["prompt"])

    def test_credit_balance_fail_closed(self):
        with patch("urllib.request.urlopen") as mock_open:
            mock_open.side_effect = ValueError("offline")
            with self.assertRaises(m.TrialBlocked):
                m.available_credits("redacted")

    def test_live_requires_authorization(self):
        args = types.SimpleNamespace(source_frame="/does/not/exist.jpg",
             source_video=None, output="/tmp/unused", confirm_trial_credits=False,
             quoted_credits=None, credit_cap=None)
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(m.TrialBlocked):
                m.live(args)

    def test_exact_sdk_call_uses_genuine_image_and_fourteen_seconds(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "last_frame.jpg"
            source.write_bytes(b"temporary fake bytes for sdk mock")
            video = Path(tmp) / "render.mp4"
            video.write_bytes(b"mock output")
            fake = types.SimpleNamespace(
                id="fake-project-id", status="complete", credits_charged=100,
                downloaded_paths=[str(video)])
            generator = MagicMock(return_value=fake)
            sdk = types.SimpleNamespace(Client=MagicMock())
            sdk.Client.return_value.v1.image_to_video.generate = generator
            args = types.SimpleNamespace(source_frame=str(source),
                source_video=None, output=str(Path(tmp) / "output"),
                quoted_credits=100, credit_cap=120, confirm_trial_credits=True)
            with patch.dict(os.environ, {"MAGIC_HOUR_API_KEY": "TEST-ONLY"}), \
                 patch.dict("sys.modules", {"magic_hour": sdk}), \
                 patch.object(m, "available_credits", return_value=200):
                m.live(args)
            kwargs = generator.call_args.kwargs
            self.assertEqual(kwargs["end_seconds"], 14)
            self.assertEqual(kwargs["resolution"], "480p")
            self.assertEqual(kwargs["model"], "ltx-2.5")
            self.assertTrue(kwargs["audio"])
            self.assertEqual(kwargs["assets"]["image_file_path"], str(source.resolve()))
            self.assertIn("same hypercar", kwargs["style"]["prompt"].lower())
            meta = json.loads((Path(args.output)/"magic_hour_job.json").read_text())
            self.assertEqual(meta["status"], "RENDERED_REQUIRES_VISUAL_RIGHTS_QC")
            self.assertFalse(meta["publish_approved"])

    def test_provider_failure_does_not_claim_delivery(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)/"actual_frame.jpg"
            source.write_bytes(b"photo")
            fake = types.SimpleNamespace(id="fake-id", status="error",
                credits_charged=0, downloaded_paths=None)
            sdk = types.SimpleNamespace(Client=MagicMock())
            sdk.Client.return_value.v1.image_to_video.generate = MagicMock(return_value=fake)
            args = types.SimpleNamespace(source_frame=str(source), source_video=None,
                output=str(Path(tmp)/"o"), quoted_credits=20, credit_cap=20,
                confirm_trial_credits=True)
            with patch.dict(os.environ, {"MAGIC_HOUR_API_KEY": "TEST-ONLY"}), \
                 patch.dict("sys.modules", {"magic_hour": sdk}), \
                 patch.object(m, "available_credits", return_value=50):
                with self.assertRaises(m.TrialBlocked):
                    m.live(args)
            info=json.loads((Path(args.output)/"magic_hour_job.json").read_text())
            self.assertEqual(info["status"], "NOT_DELIVERED_CHECK_PROVIDER_JOB_BEFORE_RETRY")


if __name__ == "__main__":
    unittest.main()
