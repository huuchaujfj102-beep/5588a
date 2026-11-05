import unittest

from oneflow.cinematic_image_rules import (GLOBAL_PREFIX, apply_global_rules, build_negative_prompt, NEGATIVE_LAYERS)
from oneflow.image_generation import build_prompt


class CinematicImageRulesTests(unittest.TestCase):
    def test_prefix_applied_to_one_sentence(self):
        result = build_prompt(brief="Golden-armored warrior in a marble temple")
        self.assertTrue(result.startswith(GLOBAL_PREFIX))
        self.assertIn("Golden-armored warrior", result)

    def test_idempotent_prefix(self):
        prompt = "a single cinematic shot"
        self.assertEqual(apply_global_rules(apply_global_rules(prompt)),
                         apply_global_rules(prompt))

    def test_plain_negative_has_no_weight_syntax(self):
        plain = build_negative_prompt()
        self.assertIn(NEGATIVE_LAYERS["A"], plain)
        self.assertNotIn(":1.4", plain)
        self.assertLess(plain.index(NEGATIVE_LAYERS["A"]), plain.index(NEGATIVE_LAYERS["D"]))

    def test_weighted_negative_requires_explicit_opt_in(self):
        weighted = build_negative_prompt(weighted=True)
        self.assertIn(":1.4)", weighted)
        self.assertIn(":1.0)", weighted)

    def test_negative_exception_layer(self):
        without_style = build_negative_prompt(exclude_layers=("D",))
        self.assertNotIn(NEGATIVE_LAYERS["D"], without_style)

    def test_negative_unknown_layer_rejected(self):
        with self.assertRaises(ValueError):
            build_negative_prompt(exclude_layers=("INVALID",))

    def test_empty_prompt_rejected(self):
        with self.assertRaises(ValueError):
            apply_global_rules("  ")


if __name__ == "__main__":
    unittest.main()
