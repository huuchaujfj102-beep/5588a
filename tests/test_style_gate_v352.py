import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from oneflow.style_gate_v352 import verify, StyleGateError, G4_CHECKS, STYLE_ID, SCHEMA


class TestV352Gate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.style = self.root / "style.png"
        self.frame = self.root / "frame.png"
        self.style.write_bytes(b"style master in test")
        self.frame.write_bytes(b"approved frame in test")
        def sha(p):
            return hashlib.sha256(p.read_bytes()).hexdigest()
        self.m = dict(schema=SCHEMA, style_id=STYLE_ID, shot_id="S05-04",
                      scene_id="COAST-01", scene_anchor="left hill and harbor",
                      lighting_contract="overcast", weather_contract="north wind rain",
                      material_contract="wet timber and stone", color_profile="cool slate",
                      camera_composition="medium wide no actors",
                      reference_binding_evidence="local composite reference file used",
                      reference_method="original_pixel_composite",
                      style_source_path="style.png", style_source_sha256=sha(self.style),
                      collage=False, text_overlay=False,
                      approved_first_frame_path="frame.png", approved_first_frame_sha256=sha(self.frame),
                      g4_status="G4_PASS_HUMAN", human_approval="APPROVED",
                      reviewer="test-reviewer", camera_motion="locked",
                      g4_checks={name:"PASS" for name in G4_CHECKS})
    def check(self, stage="video"):
        p = self.root / "m.json"
        p.write_text(json.dumps(self.m))
        return verify(p, self.root, stage)
    def test_valid_metadata_not_pixel_certification(self):
        result=self.check()
        self.assertFalse(result["visual_review_done_by_code"])
        self.assertFalse(result["reference_consumption_proven_by_code"])
    def test_image_contract_without_review(self):
        del self.m["g4_status"]
        self.assertEqual(self.check("image")["stage"],"image")
    def test_bad_style_hash_blocks(self):
        self.m["style_source_sha256"]="0"*64
        with self.assertRaisesRegex(StyleGateError,"sha256"):self.check()
    def test_missing_style_asset_blocks(self):
        self.m["style_source_path"]="missing.png"
        with self.assertRaisesRegex(StyleGateError,"unbound"):self.check()
    def test_text_only_reference_blocks(self):
        self.m["reference_method"]="prompt_only"
        with self.assertRaisesRegex(StyleGateError,"image-conditioned"):self.check()
    def test_collage_blocks(self):
        self.m["collage"]=True
        with self.assertRaisesRegex(StyleGateError,"collage"):self.check()
    def test_fake_approval_blocks(self):
        self.m["human_approval"]="PENDING"
        with self.assertRaisesRegex(StyleGateError,"human approval"):self.check()
    def test_bad_first_frame_hash_blocks(self):
        self.m["approved_first_frame_sha256"]="f"*64
        with self.assertRaisesRegex(StyleGateError,"sha256"):self.check()
    def test_incomplete_g4_blocks(self):
        self.m["g4_checks"]["identity"]="NEEDS_EVIDENCE"
        with self.assertRaisesRegex(StyleGateError,"G4 checks"):self.check()
    def test_path_escape_blocks(self):
        self.m["style_source_path"]="../private.png"
        with self.assertRaisesRegex(StyleGateError,"unbound"):self.check()


if __name__ == "__main__":
    unittest.main()
