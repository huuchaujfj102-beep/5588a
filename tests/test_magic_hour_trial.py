import unittest
from unittest.mock import patch
from oneflow import magic_hour_trial as m


class MagicHourTrialTests(unittest.TestCase):
    def test_preview_is_not_marked_rendered_or_licensed(self):
        p = m.plan()
        self.assertEqual(p["duration_seconds"], 14)
        self.assertEqual(p["status"], "PREPARED_NOT_AUTHORIZED_NOT_RENDERED")
        self.assertIn("NONCOMMERCIAL", p["license_gate"])
        self.assertIn("EXACT ORIGINAL", p["prompt"])

    def test_credit_balance_fail_closed(self):
        with patch("urllib.request.urlopen") as mock_open:
            mock_open.side_effect = ValueError("offline")
            with self.assertRaises(m.TrialBlocked):
                m.available_credits("redacted")

    def test_live_requires_authorization(self):
        class Args:
            source_frame = "/does/not/exist.jpg"
            confirm_trial_credits = False
            quoted_credits = None
            credit_cap = None
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(m.TrialBlocked):
                m.live(Args())


if __name__ == "__main__":
    unittest.main()
