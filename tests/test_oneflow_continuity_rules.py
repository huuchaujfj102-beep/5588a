"""Offline regressions for prop errors and intended fantasy in public prompt paths."""
import unittest

from oneflow.director import film_prompt
from oneflow.image_generation import build_prompt, prompt_from_request
from oneflow.continuity_rules import specialist_constraints, negative_constraints


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
        self.assertIn("straight rigid parts", prompt)
        self.assertIn("contradictory perspective", prompt)

    def test_traditional_chinese_prop_names(self):
        self.assertIn("hair attached at ONE end only", specialist_constraints("手持拂塵"))
        self.assertIn("both rim ends", specialist_constraints("花籃"))


if __name__ == "__main__":
    unittest.main()
