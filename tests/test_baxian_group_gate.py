"""Tests use synthetic local PNGs; they do NOT certify production images."""
import copy
import hashlib
import json
import struct
import tempfile
import unittest
import zlib
from pathlib import Path

from film_audit.baxian_group_gate import validate


def png_bytes(width=160, height=90, color=6):
    channels = 4 if color == 6 else 1
    pixels = b"".join(b"\x00" + bytes([44] * (width * channels)) for _ in range(height))
    def chunk(kind, payload):
        return (struct.pack(">I", len(payload)) + kind + payload +
                struct.pack(">I", zlib.crc32(kind + payload) & 0xffffffff))
    return (b"\x89PNG\r\n\x1a\n" +
            chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, color, 0, 0, 0)) +
            chunk(b"IDAT", zlib.compress(pixels)) + chunk(b"IEND", b""))


class BaxianGroupGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        policy_path = Path("film_audit/assets/baxian_group_enforcement_policy_v3.json")
        self.policy = json.loads(policy_path.read_text(encoding="utf-8"))
        self.authority = {"asset_rows": [], "file_hashes": []}
        self.plan = {
            "schema_version": 3, "mode": "layered_composite", "ratio": "16:9",
            "shot_id": "TEST-S04",
            "scene": {"background_file": "scene.png", "sha256": "",
                      "world_axis": "west_shore_camera_facing_east",
                      "sun": "upper_right", "wind": "right_to_left"},
            "actors": [],
            "output": {"file": "finished.png", "sha256": ""},
            "review": {"p0_count": None, "p1_count": None,
                       "roles": {}, "category_checks": {}},
        }
        self.plan["scene"]["sha256"] = self.put_png("scene.png")
        self.plan["output"]["sha256"] = self.put_png("finished.png")
        for placement in self.policy["layout"]:
            aid = placement["id"]
            row = {"id": aid, "hero": aid + "_hero.png",
                   "turnaround": aid + "_views.png", "prop": aid + "_prop.png"}
            self.authority["asset_rows"].append(row)
            for role, source in (("hero", row["hero"]), ("views", row["turnaround"]),
                                 ("prop", row["prop"])):
                digest = self.put_png(source)
                self.authority["file_hashes"].append(
                    {"id": aid, "role": role, "filename": source, "sha256": digest})
            layers = {}
            for item in ("character", "prop"):
                name = aid + "_" + item
                path = "layers/" + name + ".png"
                mask_path = "masks/" + name + "_mask.png"
                layers[item] = {"file": path, "sha256": self.put_png(path),
                                "mask": mask_path,
                                "mask_sha256": self.put_png(mask_path, color=0)}
            actor = dict(placement)
            actor["special_action"] = self.policy["special_actions"][aid]
            actor["orientation"] = ("backward_facing_donkey_tail"
                                    if aid == "BX05" else "per_approved_source")
            actor["props"] = list(self.policy["props"][aid])
            actor["sources"] = {"hero": row["hero"], "views": row["turnaround"],
                                "prop": row["prop"]}
            actor["locked_layers"] = layers
            self.plan["actors"].append(actor)

    def put_png(self, name, color=6):
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        content = png_bytes(color=color)
        p.write_bytes(content)
        return hashlib.sha256(content).hexdigest()

    def result(self, phase="preflight"):
        return validate(self.plan, self.authority, self.policy, self.root, phase)

    def codes(self, result):
        return [x["code"] for x in result["issues"]]

    def test_valid_preflight(self):
        result = self.result()
        self.assertEqual(result["status"], "PREFLIGHT_PASS")
        self.assertTrue(result["may_generate"])
        self.assertFalse(result["may_merge_final_or_start_i2v"])

    def test_wrong_prop_ownership_blocks(self):
        actor = next(a for a in self.plan["actors"] if a["id"] == "BX04")
        actor["props"] = ["single_white_donkey"]
        self.assertIn("PROP_OWNER_OR_COUNT", self.codes(self.result()))

    def test_wrong_reference_and_hash_blocks(self):
        self.plan["actors"][0]["sources"]["hero"] = "BX02_hero.png"
        self.assertIn("SOURCE_BINDING_DRIFT", self.codes(self.result()))
        self.plan["actors"][0]["sources"]["hero"] = "BX01_hero.png"
        (self.root / "BX01_hero.png").write_bytes(b"changed")
        self.assertIn("HASH_MISMATCH", self.codes(self.result()))

    def test_missing_approved_original_blocks(self):
        (self.root / "BX01_prop.png").unlink()
        self.assertIn("MISSING_ASSET", self.codes(self.result()))

    def test_missing_rgba_layer_or_mask_blocks(self):
        (self.root / "layers/BX03_character.png").unlink()
        self.assertEqual(self.result()["status"], "BLOCKED")
        self.assertIn("MISSING_ASSET", self.codes(self.result()))

    def test_character_layer_cannot_be_rgb(self):
        layer = self.plan["actors"][0]["locked_layers"]["character"]
        layer["sha256"] = self.put_png(layer["file"], color=0)
        self.assertIn("LAYER_NOT_RGBA", self.codes(self.result()))

    def test_full_frame_regeneration_rejected(self):
        self.plan["mode"] = "text_to_image_group_redraw"
        self.assertIn("FULL_FRAME_REGEN_FORBIDDEN", self.codes(self.result()))

    def test_layout_and_backwards_riding_enforced(self):
        actor = next(a for a in self.plan["actors"] if a["id"] == "BX05")
        actor["orientation"] = "forward"
        self.assertIn("DONKEY_REVERSE_RIDING_MISSING", self.codes(self.result()))
        actor["orientation"] = "backward_facing_donkey_tail"
        actor["row"] = "front"
        self.assertIn("BLOCKING_DRIFT", self.codes(self.result()))

    def test_duplicate_actor_rejected(self):
        self.plan["actors"][-1] = copy.deepcopy(self.plan["actors"][0])
        self.assertIn("CAST_COUNT_OR_ID", self.codes(self.result()))

    def test_postflight_requires_review(self):
        self.plan["review"]["p0_count"] = 0
        self.plan["review"]["p1_count"] = 0
        result = self.result("postflight")
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertFalse(result["may_submit_to_user"])

    def test_postflight_p0_blocks(self):
        self.plan["review"]["p0_count"] = 1
        self.plan["review"]["p1_count"] = 0
        self.assertIn("P0_NOT_CLEARED", self.codes(self.result("postflight")))

    def test_evidence_completeness_only_allows_user_review(self):
        self.plan["review"]["p0_count"] = 0
        self.plan["review"]["p1_count"] = 0
        evidence_sha = self.put_png("qa/evidence.png")
        self.assertTrue(evidence_sha)
        for role in self.policy["review_roles"]:
            self.plan["review"]["roles"][role] = {
                "status": "PASS", "evidence_file": "qa/evidence.png"}
        for kind in self.policy["post_review_required"]:
            self.plan["review"]["category_checks"][kind] = "PASS"
        for aid in [row["id"] for row in self.policy["layout"]]:
            name = "qa/evidence_" + aid + ".png"
            self.put_png(name)
            self.plan["review"].setdefault("actor_checks", {})[aid] = {
                **{k: "PASS" for k in self.policy["per_actor_review_required"]},
                "evidence_file": name,
            }
        result = self.result("postflight")
        self.assertEqual(result["status"], "READY_FOR_USER_REVIEW")
        self.assertTrue(result["may_submit_to_user"])
        self.assertFalse(result["may_merge_final_or_start_i2v"])

    def test_path_traversal_blocked(self):
        self.plan["scene"]["background_file"] = "../outside.png"
        self.assertIn("PATH_ESCAPE", self.codes(self.result()))


    def test_actor_specific_failure_blocks_release(self):
        self.plan["review"]["p0_count"] = 0
        self.plan["review"]["p1_count"] = 0
        self.plan["review"]["actor_checks"] = {"BX05": {"prop_shape_count": "FAIL"}}
        self.assertIn("ACTOR_REVIEW_FAILED", self.codes(self.result("postflight")))

    def test_composite_preserves_source_layers_and_refuses_overwrite(self):
        try:
            from PIL import Image, ImageDraw
        except ImportError:
            self.skipTest("Pillow is not installed")
        from film_audit.baxian_layered_composite import composite_locked_layers

        for actor in self.plan["actors"]:
            for kind in ("character", "prop"):
                layer = actor["locked_layers"][kind]
                canvas = Image.new("RGBA", (160, 90), (0, 0, 0, 0))
                draw = ImageDraw.Draw(canvas)
                draw.rectangle((20, 12, 44, 70), fill=(12, 60, 100, 255))
                loc = self.root / layer["file"]
                canvas.save(loc)
                layer["sha256"] = hashlib.sha256(loc.read_bytes()).hexdigest()

                matte = Image.new("L", (160, 90), 0)
                draw_mask = ImageDraw.Draw(matte)
                draw_mask.rectangle((20, 12, 44, 70), fill=255)
                mloc = self.root / layer["mask"]
                matte.save(mloc)
                layer["mask_sha256"] = hashlib.sha256(mloc.read_bytes()).hexdigest()

        before = [(a["id"], a["locked_layers"]["character"]["sha256"])
                  for a in self.plan["actors"]]
        result = composite_locked_layers(
            self.plan, self.authority, self.policy, self.root, "finished.png")
        self.assertEqual(result["status"], "BLOCKED")  # existing source output protected
        self.plan["output"]["file"] = "outputs/fresh_group_candidate.png"
        result = composite_locked_layers(
            self.plan, self.authority, self.policy, self.root,
            "outputs/fresh_group_candidate.png")
        self.assertEqual(result["status"], "CANDIDATE_RENDERED_NOT_APPROVED")
        self.assertTrue((self.root / "outputs/fresh_group_candidate.png").exists())
        after = [(a["id"], a["locked_layers"]["character"]["sha256"])
                 for a in self.plan["actors"]]
        self.assertEqual(before, after)
        self.assertFalse(result["may_start_i2v"])
        again = composite_locked_layers(
            self.plan, self.authority, self.policy, self.root,
            "outputs/fresh_group_candidate.png")
        self.assertEqual(again["status"], "BLOCKED")

if __name__ == "__main__":
    unittest.main()
