"""Offline fail-closed checks; no model providers or paid calls."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from oneflow.production_qa_gate import check_manifest, QAGateError, GATES


class ProductionGates(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "asset.png").write_bytes(b"approved mother pixels")
        self.doc = {
            "schema": "oneflow-qa-v3", "shot_id": "BXDG_G11",
            "assets": [{"asset_id": "BX05", "path": "asset.png",
                        "sha256": hashlib.sha256(b"approved mother pixels").hexdigest()}],
            "scene_id": "STORM_COAST", "camera_id": "CAM_01",
            "lighting_id": "LIGHT_01", "palette_id": "COL_01",
            "previous_shot_state": "continuous", "change_scope": "background only",
            "seven_gates": {key: "PASS" for key in GATES},
            "p0_open": 0, "p1_open": 0, "human_approval": "APPROVED",
            "reviewer_id": "reviewer-in-test", "reviewed_utc": "2026-11-11T00:00:00Z",
        }

    def check(self):
        p = self.root / "manifest.json"
        p.write_text(json.dumps(self.doc), encoding="utf-8")
        return check_manifest(p, root=self.root)

    def test_pass_is_only_metadata_not_visual_certification(self):
        result = self.check()
        self.assertFalse(result["visual_identity_verified_by_code"])
        self.assertFalse(result["paid_task_created"])

    def test_hash_drift_blocks(self):
        self.doc["assets"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(QAGateError, "SHA256"):
            self.check()

    def test_unapproved_blocks(self):
        self.doc["human_approval"] = "REVIEW_REQUIRED"
        with self.assertRaisesRegex(QAGateError, "human approval"):
            self.check()

    def test_seven_gate_blocks(self):
        for key in GATES:
            self.doc["seven_gates"][key] = "FAIL"
            with self.subTest(key=key), self.assertRaisesRegex(QAGateError, key):
                self.check()
            self.doc["seven_gates"][key] = "PASS"

    def test_unresolved_issues_block(self):
        self.doc["p0_open"] = 1
        with self.assertRaisesRegex(QAGateError, "P0/P1"):
            self.check()

    def test_missing_asset_blocks(self):
        self.doc["assets"][0]["path"] = "not-present.png"
        with self.assertRaisesRegex(QAGateError, "unavailable"):
            self.check()

    def test_path_escape_blocks(self):
        self.doc["assets"][0]["path"] = "../secret.png"
        with self.assertRaisesRegex(QAGateError, "outside workspace"):
            self.check()

    def test_missing_scene_card_blocks(self):
        del self.doc["lighting_id"]
        with self.assertRaisesRegex(QAGateError, "lighting_id"):
            self.check()


if __name__ == "__main__":
    unittest.main()
