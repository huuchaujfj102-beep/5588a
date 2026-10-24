import tempfile
import unittest
from pathlib import Path
from film_audit.audit import ms, check_srt, check_assets

class AuditTests(unittest.TestCase):
    def test_srt_timestamp(self):
        self.assertEqual(ms("00:00:03,500"), 3500)
    def test_invalid_srt(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"bad.srt"
            p.write_text("1\n00:00:02,000 --> 00:00:01,000\n错误\n", encoding="utf8")
            self.assertTrue(any(i["code"]=="NEGATIVE_DURATION" for i in check_srt(p)))
    def test_missing_ledger(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(check_assets(Path(d)/"absent.csv")[0]["code"], "MISSING_LEDGER")
    def test_ledger_complete(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"assets.csv"
            p.write_text("asset_id,source,license,proof,usage_scope\n1,own,owned,receipt,video\n")
            self.assertEqual(check_assets(p), [])
if __name__ == "__main__":
    unittest.main()
