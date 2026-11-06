"""Offline regressions for prop errors and intended fantasy in public prompt paths."""
import unittest

from oneflow.director import film_prompt
from oneflow.image_generation import build_prompt, prompt_from_request
from oneflow.continuity_rules import specialist_constraints, negative_constraints, compile_prompt


class ContinuityRulesTests(unittest.TestCase):
    def test_back_sword_and_whisk_reach_image_and_video_prompts(self):
        brief = "吕洞宾背负大剑、手持拂尘，站在山巅"
        for prompt in (build_prompt(brief), film_prompt(brief, "持拂尘", None, 1, 1)):
            self.assertIn("grip/guard/mouth/sheath on one straight axis", prompt)
            self.assertIn("hair attached at ONE end only", prompt)
            self.assertEqual(prompt.count("Back sword:"), 1)

    def test_fantasy_is_preserved_without_unrelated_prop_instructions(self):
        brief = "仙人踏云，仙山悬浮，花瓣漂浮"
        prompt = build_prompt(brief)
        self.assertIn(brief, prompt)
        self.assertIn("levitation and transformations remain allowed", prompt)
        self.assertNotIn("Back sword:", prompt)
        self.assertNotIn("Fly-whisk:", prompt)
        self.assertNotIn("levitation", negative_constraints(motion=True))

    def test_basket_specialist_is_selected_without_sword_rules(self):
        prompt = film_prompt("蓝采和手持花篮", "站稳", None, 1, 1)
        self.assertIn("both rim ends", prompt)
        self.assertIn("contact points and action state", prompt)
        self.assertNotIn("Back sword:", prompt)
        self.assertIn("7. Negative constraints:", prompt)

    def test_existing_storyboard_path_gets_generic_structural_rules(self):
        prompt = prompt_from_request("oneflow/requests/snow-white-seven-dwarfs-60s.json", "S01")
        self.assertIn("rigid parts collinear", prompt)
        self.assertIn("contradictory perspective", prompt)

    def test_traditional_chinese_prop_names(self):
        self.assertIn("hair attached at ONE end only", specialist_constraints("手持拂塵"))
        self.assertIn("both rim ends", specialist_constraints("花籃"))

    def test_hem_does_not_hide_duplicate_shoes_in_generation_contract(self):
        brief = "吕洞宾长袍站立，铁拐李跛足扶拐，保留两人各自腿脚设定"
        for prompt in (build_prompt(brief), film_prompt(brief, "站立", None, 1, 1)):
            self.assertIn("each shoe has one upper and one sole", prompt)
            self.assertIn("preserve intentional limb differences", prompt)
            self.assertIn(brief, prompt)
        self.assertIn("duplicated soles", negative_constraints())

    def test_compilation_idempotent_and_stage_modes_replace_one_block(self):
        source = "二次元横图，招牌文字望花楼，造镜者水印，仙人瞬移"
        once = compile_prompt(source)["prompt"]
        self.assertEqual(once, compile_prompt(once)["prompt"])
        video = compile_prompt(once, stage="video", separate_negative=True)
        self.assertTrue(video["prompt"].startswith(source))
        self.assertEqual(video["prompt"].count("[OneFlow rules v2:"), 1)
        self.assertNotIn(" Avoid: ", video["prompt"])
        self.assertIn("unexplained teleportation", video["negative_prompt"])

    def test_budget_never_cuts_user_source_or_specialist(self):
        source = "手持拂尘。" + "甲" * 1300
        result = compile_prompt(source, max_chars=2048)
        self.assertTrue(result["prompt"].startswith(source))
        self.assertIn("hair attached at ONE end only", result["prompt"])
        self.assertLessEqual(len(result["prompt"]), 2048)
        with self.assertRaisesRegex(ValueError, "source not truncated"):
            compile_prompt("甲" * 2048, max_chars=2048)

    def test_carried_non_sword_and_negated_props_do_not_create_swords(self):
        self.assertNotIn("Back sword:", specialist_constraints("铁拐李背负葫芦"))
        self.assertEqual(specialist_constraints("不要背剑；不要花篮；without a fly-whisk"), "")
        self.assertEqual(specialist_constraints("花篮不入镜"), "")
        self.assertNotIn("donkey", specialist_constraints("倒骑青牛"))

    def test_static_camera_and_requested_framing_are_not_overridden(self):
        prompt = film_prompt("固定镜头、半身特写，快速挥动拂尘", "挥动", None, 1, 1)
        self.assertIn("including static", prompt)
        self.assertNotIn("feet without accidental cropping", prompt)
        self.assertNotIn("Photorealistic", prompt)

    def test_image_to_video_handoff_extracts_v2_source_not_rule_text(self):
        from oneflow.handoff import original_brief
        brief = "  吕洞宾持拂尘。固定镜头。  "
        extracted = original_brief({"prompt": build_prompt(brief)})
        self.assertEqual(extracted, brief)
        self.assertNotIn("OneFlow rules", extracted)

    def test_recompiling_preserves_character_notes_between_rule_blocks(self):
        prompt = film_prompt("吕洞宾手持拂尘", "站立", None, 1, 1)
        notes = "\n全片人物设定：独有青玉发簪XYZ；允许造镜者水印。"
        source = prompt + notes
        video = compile_prompt(source, stage="video")["prompt"]
        image = compile_prompt(video, stage="image")["prompt"]
        for result in (video, image):
            self.assertIn(notes, result)
            self.assertEqual(result.count("[OneFlow rules v2:"), 1)
        # Also recover old duplicate-block artifacts without losing intervening notes.
        legacy = prompt + notes + compile_prompt("额外场景")["prompt"]
        repaired = compile_prompt(legacy, stage="image")["prompt"]
        self.assertIn(notes, repaired)
        self.assertIn("额外场景", repaired)
        self.assertEqual(repaired.count("[OneFlow rules v2:"), 1)


if __name__ == "__main__":
    unittest.main()
