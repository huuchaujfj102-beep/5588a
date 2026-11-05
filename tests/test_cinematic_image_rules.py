import unittest

from oneflow.cinematic_image_rules import GLOBAL_PREFIX, apply_global_rules
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

    def test_empty_prompt_rejected(self):
        with self.assertRaises(ValueError):
            apply_global_rules("  ")


if __name__ == "__main__":
    unittest.main()
