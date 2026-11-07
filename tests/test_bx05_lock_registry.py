"""Registry regressions; no claim that unavailable hero pixels were reviewed."""
import json
import unittest
from pathlib import Path


def load(name):
    return json.loads(Path(name).read_text(encoding="utf-8"))


class BX05RegistryTests(unittest.TestCase):
    def test_legacy_mapping_and_hashes_preserved(self):
        authority = load("film_audit/assets/baxian_source_authority_v2_20261107.json")
        expected = {
            "1000023552.png": "0bef1029b7687df4c5a728bce3c61f5349b918dc16ae2e3e598ea1b04ccb9199",
            "1000023558.png": "be61023f2b51a0346f81bab7c6ceff956e4fe79a9293a3260b5941fa34774ac6",
            "1000023545.png": "0073ab42efa02c2a631648355ff235690ca4008c0185a476582a2129be038e64"}
        self.assertEqual({r["filename"]: r["sha256"] for r in authority["file_hashes"]
                          if r["id"] == "BX05" and r["role"] in ("hero", "views", "prop")}, expected)
        row = next(r for r in authority["asset_rows"] if r["id"] == "BX05")
        self.assertEqual([row[k] for k in ("hero", "turnaround", "prop")], list(expected))

    def test_approval_does_not_invent_binary_binding(self):
        authority = load("film_audit/assets/baxian_source_authority_v2_20261107.json")
        lock = authority["character_locks"]["BX05"]
        detail = load(lock["manifest_path"])
        rules = next(r for r in load("film_audit/baxian_character_rules.json")["characters"] if r["id"] == "BX05")
        self.assertEqual(lock["current_hero"], detail["current_hero"])
        self.assertEqual(lock["current_hero"], rules["current_hero"])
        self.assertEqual(detail["approval_evidence"]["user_quote"], "可以写入张果老人物定型")
        self.assertIsNone(detail["current_hero"]["sha256"])
        self.assertFalse(detail["mapping_audit"]["originals_rehashed"])
        self.assertEqual(lock["references"], detail["references"])
        self.assertEqual(len(detail["references"]), 2)
        self.assertNotIn("小鼓", rules["forbidden"])
        self.assertIn("斑点竹筒鱼鼓", rules["required"])

    def test_group_template_matches_v4_policy(self):
        policy = load("film_audit/assets/baxian_group_enforcement_policy_v3.json")
        plan = load("film_audit/shots/s04_01_layered_group_plan_TEMPLATE.json")
        actor = next(a for a in plan["actors"] if a["id"] == "BX05")
        self.assertEqual(actor["props"], policy["props"]["BX05"])
        self.assertEqual(actor["prop_details"], policy["prop_details"]["BX05"])
        self.assertEqual(actor["lock_version"], policy["character_lock_versions"]["BX05"])
        self.assertIsNone(actor["sources"]["current_hero"])
        for field in policy["per_actor_extra_review_required"]["BX05"]:
            self.assertNotEqual(plan["review"]["actor_checks"]["BX05"][field], "PASS")
