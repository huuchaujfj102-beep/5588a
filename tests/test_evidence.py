import json
import tempfile
import unittest
from pathlib import Path

from film_audit.evidence import build_result, verify_evidence


class EvidenceTests(unittest.TestCase):
    def test_empty_manifest_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "evidence.json"
            path.write_text("{}", encoding="utf-8")
            result = build_result(path)
            self.assertEqual(result["status"], "FAIL")
            codes = {x["code"] for x in result["issues"]}
            self.assertIn("RULES_NOT_67", codes)
            self.assertIn("FINAL_FILMS_INCOMPLETE", codes)
            self.assertIn("HUMAN_REVIEWS_INCOMPLETE", codes)

    def test_rule_count_requires_exact_sequence(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "evidence.json"
            path.write_text(json.dumps({"rules": [{"number": 1}]}), encoding="utf-8")
            self.assertTrue(any(x["code"] == "RULES_NOT_67" for x in verify_evidence(path)))


if __name__ == "__main__":
    unittest.main()

