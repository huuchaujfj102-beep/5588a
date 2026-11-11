"""Offline Baxian V3.1-V3.5 metadata gate regression tests."""
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from oneflow.production_qa_gate import check_manifest, QAGateError, GATES
from oneflow.baxian_scene_gate import BaxianSceneGateError, HARD_CHECKS


class BaxianGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.assets = []
        for i in range(1, 9):
            name = "BX%02d" % i
            data = (name + "_approved_master_mock").encode()
            (self.root / (name + ".png")).write_bytes(data)
            self.assets.append({"asset_id": name, "path": name + ".png",
                                "sha256": hashlib.sha256(data).hexdigest()})
        self.doc = {
            "schema": "oneflow-qa-v3", "project_id": "baxian",
            "shot_id": "S03-01",
            "assets": copy.deepcopy(self.assets),
            "scene_id": "STORM_COAST", "camera_id": "CAM_SOUTH",
            "lighting_id": "LIGHT_STORM", "palette_id": "COLOR_STORM",
            "previous_shot_state": "ASSEMBLED_8",
            "change_scope": "background compositing only",
            "seven_gates": {n: "PASS" for n in GATES},
            "p0_open": 0, "p1_open": 0,
            "human_approval": "APPROVED", "reviewer_id": "test-only",
            "reviewed_utc": "2026-11-11T00:00:00Z",
            "story_phase": "ASSEMBLED_8",
            "battlefield_contract": {
                "period_system": "approved LOCK V2 costumes",
                "aspect_ratio": "16:9", "camera_axis": "south",
                "physical_key_light": "storm upper left",
                "ground_surfaces": "coastal rock and shallow water",
                "fog_layers": "spray / mist / rain",
                "wind_vector": "screen right",
                "faction_palette": "LOCK V2 original palettes",
            },
            "character_positions": [
                {"character_id": x["asset_id"],
                 "master_sha256": x["sha256"],
                 "artifact_group": "LOCK V2 " + x["asset_id"],
                 "facing": "toward black tide",
                 "depth_layer": "front" if i < 3 else "middle",
                 "occlusion": "none, full silhouette"}
                for i, x in enumerate(self.assets)
            ],
            "supplemental_gates": {
                **{group: {field: "PASS" for field in fields}
                   for group, fields in HARD_CHECKS.items()},
                "G4C": {"reviewed": "PASS", "hard_defects": 0,
                        "art_notes": "Mock-only data; no pixel review claimed"},
            },
        }

    def run_gate(self):
        path = self.root / "qa.json"
        path.write_text(json.dumps(self.doc, ensure_ascii=False), encoding="utf-8")
        return check_manifest(path, root=self.root)

    def test_complete_metadata_not_visual_approval(self):
        result = self.run_gate()
        self.assertEqual(result["status"], "PREFLIGHT_PASS_METADATA_ONLY")
        self.assertFalse(result["visual_identity_verified_by_code"])
        self.assertEqual(result["supplemental"]["checked_groups"][-1], "G4C")

    def test_missing_battlefield_contract_blocks(self):
        del self.doc["battlefield_contract"]["wind_vector"]
        with self.assertRaisesRegex(BaxianSceneGateError, "wind_vector"):
            self.run_gate()

    def test_locked_ratio_cannot_change_without_order(self):
        self.doc["battlefield_contract"]["aspect_ratio"] = "2.35:1"
        with self.assertRaisesRegex(BaxianSceneGateError, "16:9"):
            self.run_gate()

    def test_missing_person_in_eight_assembly_blocks(self):
        self.doc["character_positions"].pop()
        with self.assertRaisesRegex(BaxianSceneGateError, "missing characters"):
            self.run_gate()

    def test_identity_hash_mismatch_blocks(self):
        self.doc["character_positions"][0]["master_sha256"] = "f" * 64
        with self.assertRaisesRegex(BaxianSceneGateError, "hash"):
            self.run_gate()

    def test_duplication_blocks(self):
        self.doc["character_positions"][0] = self.doc["character_positions"][1]
        with self.assertRaisesRegex(BaxianSceneGateError, "duplicated"):
            self.run_gate()

    def test_capture_arc_not_implicitly_approved(self):
        self.doc["story_phase"] = "RESCUE_7"
        self.doc["character_positions"] = [x for x in self.doc["character_positions"]
                                            if x["character_id"] != "BX04"]
        with self.assertRaisesRegex(BaxianSceneGateError, "not approved"):
            self.run_gate()

    def test_captive_character_cannot_fight_during_rescue(self):
        self.doc["story_phase"] = "RESCUE_7"
        self.doc["script_change_order"] = "APPROVED"
        with self.assertRaisesRegex(BaxianSceneGateError, "cannot be"):
            self.run_gate()

    def test_missing_g4b_blocks(self):
        self.doc["supplemental_gates"]["G4B"]["lotus_basket_ownership"] = "NEEDS_EVIDENCE"
        with self.assertRaisesRegex(BaxianSceneGateError, "lotus_basket"):
            self.run_gate()

    def test_artistic_review_cannot_replace_identity_check(self):
        self.doc["seven_gates"]["identity"] = "FAIL"
        with self.assertRaisesRegex(QAGateError, "identity"):
            self.run_gate()

    def test_art_notes_required_not_mandatory_fake_film_look(self):
        self.doc["supplemental_gates"]["G4C"]["art_notes"] = None
        with self.assertRaisesRegex(BaxianSceneGateError, "art observations"):
            self.run_gate()


if __name__ == "__main__":
    unittest.main()
